from __future__ import annotations

import json
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Protocol
from urllib import error, request

from .answer_control import AnswerPlan, AnswerState
from .config import GenerationLaneSettings, GenerationSettings
from .prompts import PromptBuilder
from .types import AnswerDraft, CompiledKnowledge, ContextRoute, KnowledgePack, SessionBriefing


class LLMProvider(Protocol):
    def starter(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
        stream_state: StarterStreamState | None = None,
    ) -> AnswerDraft: ...

    def full(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
    ) -> AnswerDraft: ...


@dataclass(slots=True)
class DraftOutcome:
    draft: AnswerDraft
    latency_ms: float


@dataclass(slots=True)
class StarterStreamSnapshot:
    raw_text: str
    parsed_text: str
    updated_at: float | None
    first_partial_at_perf: float | None


@dataclass(slots=True)
class StarterStreamState:
    raw_text: str = ""
    parsed_text: str = ""
    updated_at: float | None = None
    first_partial_at_perf: float | None = None
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def ingest(self, raw_text: str, *, parsed_text: str = "") -> None:
        with self._lock:
            self.raw_text = raw_text
            self.parsed_text = parsed_text
            self.updated_at = time.time()
            if parsed_text.strip() and self.first_partial_at_perf is None:
                self.first_partial_at_perf = time.perf_counter()

    def snapshot(self) -> StarterStreamSnapshot:
        with self._lock:
            return StarterStreamSnapshot(
                raw_text=self.raw_text,
                parsed_text=self.parsed_text,
                updated_at=self.updated_at,
                first_partial_at_perf=self.first_partial_at_perf,
            )


@dataclass(slots=True)
class DraftFutures:
    turn_id: str
    starter_future: Future[DraftOutcome]
    full_future: Future[DraftOutcome]
    started_at: float
    starter_stream_state: StarterStreamState | None = None


@dataclass(slots=True)
class StarterPrewarm:
    turn_id: str
    question: str
    starter_future: Future[DraftOutcome]
    started_at: float
    starter_stream_state: StarterStreamState | None = None


class TemplateLLMProvider:
    """Deterministic fallback provider until a real model adapter is wired in."""

    def __init__(self, persona: str) -> None:
        self.persona = persona

    def starter(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
        stream_state: StarterStreamState | None = None,
    ) -> AnswerDraft:
        del stream_state
        del answer_state
        plan = self._effective_plan(answer_plan)
        project_label = self._project_label(pack, briefing)
        evidence = self._evidence_labels(pack)
        history_hint = self._history_hint(candidate_history)
        text = " ".join(
            item
            for item in [
                self._starter_opening(plan, project_label),
                history_hint,
                self._starter_detail(plan, evidence),
                self._closing_phrase(plan),
            ]
            if item
        )
        return AnswerDraft(
            level="starter",
            turn_id=turn_id,
            text=text,
            bullets=self._starter_bullets(plan),
            evidence_refs=self._evidence_ids(pack),
        )

    def full(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
    ) -> AnswerDraft:
        del answer_state
        plan = self._effective_plan(answer_plan)
        project_label = self._project_label(pack, briefing)
        module_label = self._module_label(pack)
        evidence = self._evidence_labels(pack)
        route_reason = route.reason.rstrip("。！？!? ")
        history_hint = self._history_hint(candidate_history, quoted=True)
        text = " ".join(
            item
            for item in [
                self._full_opening(plan, question, project_label, module_label),
                history_hint,
                self._full_detail(plan, route_reason, evidence, module_label),
                self._closing_phrase(plan),
            ]
            if item
        )
        return AnswerDraft(
            level="full",
            turn_id=turn_id,
            text=text,
            bullets=self._full_bullets(plan, briefing, module_label),
            evidence_refs=self._evidence_ids(pack),
        )

    def _effective_plan(self, answer_plan: AnswerPlan | None) -> AnswerPlan:
        if answer_plan is not None:
            return answer_plan
        return AnswerPlan(
            intent="generic_behavior",
            retrieve_priority=["RetrievalUnit", "Project", "RolePlaybook"],
            answer_template=["conclusion", "evidence", "boundary"],
            max_sentences=4,
            need_metrics=False,
            need_code_evidence=False,
            allow_hook=False,
        )

    def _project_label(self, pack: KnowledgePack, briefing: SessionBriefing) -> str:
        if pack.project_refs:
            return f"{pack.project_refs[0].label} 这个项目"
        if briefing.priority_projects:
            return f"{briefing.priority_projects[0]} 这个项目"
        if pack.role_refs:
            return f"{briefing.company or '这个岗位'}更看重的能力点"
        return "当前这个方向"

    def _module_label(self, pack: KnowledgePack) -> str:
        if pack.module_refs:
            return pack.module_refs[0].label
        return "这个核心模块"

    def _history_hint(self, candidate_history: list[str], *, quoted: bool = False) -> str:
        if not candidate_history:
            return ""
        if quoted:
            return f"我也会接着刚才提到的“{candidate_history[-1][:60]}”继续往下讲。"
        return "我也会承接刚才那条主线，不会把话题突然跳开。"

    def _starter_opening(self, plan: AnswerPlan, project_label: str) -> str:
        if plan.opening_move == "responsibility_first":
            return f"先说模块职责，{project_label}里我会先把它在整条链路中的位置讲清楚。"
        if plan.opening_move == "failure_first":
            return f"先说出过的问题，{project_label}里我会先把当时最痛的故障点讲清楚。"
        if plan.opening_move == "limit_first":
            return f"先说当前限制，{project_label}现在最值得继续优化的点我会先挑明。"
        if plan.delivery_style == "spoken_tradeoff":
            return f"先说结论，{project_label}我当时是做了明确取舍的。"
        if plan.delivery_style == "spoken_evidence":
            return f"先给结果，{project_label}这块我会先把指标和测量口径说清楚。"
        if plan.delivery_style == "spoken_confident":
            return f"我先用一句话概括，{project_label}本质上是在真实约束下把结果做出来。"
        return f"先说结论，{project_label}我会先把当前真实做法讲清楚。"

    def _starter_detail(self, plan: AnswerPlan, evidence: list[str]) -> str:
        evidence_hint = f" 我会先引用像 {evidence[0]} 这样的现成证据。" if evidence else ""
        if plan.intent == "tradeoff_reasoning":
            return "核心取舍不是一开始就堆最重的方案，而是先保住调试性、扩展性和落地速度。" + evidence_hint
        if plan.intent == "module_deep_dive":
            return "我会顺着职责、调用链和风险点往下讲，先把为什么它会卡在中间层说清楚。" + evidence_hint
        if plan.intent == "performance_evidence":
            return "我会直接拿指标、基线和测量方法来回答，不会只给一个漂亮结果。" + evidence_hint
        if plan.intent == "failure_analysis":
            return "我会先说真实踩过的坑，再说怎么兜底，以及后来怎么把它收敛住。" + evidence_hint
        if plan.intent == "optimization_plan":
            return "我会先讲当前限制，再讲下一步最值得做的升级动作和预期收益。" + evidence_hint
        if plan.intent == "project_intro":
            return "我会先讲业务目标，再讲方案和结果，最后留一个可以继续深挖的点。" + evidence_hint
        return "我会先讲当前做法，再补为什么这么做，以及还有哪些边界没必要说满。" + evidence_hint

    def _closing_phrase(self, plan: AnswerPlan) -> str:
        if plan.closing_move == "invite_followup":
            return "如果你想继续追问，我可以再往模块细节、指标口径或者升级路线展开。"
        if plan.closing_move == "risk_boundary":
            return "如果继续往下问，我会重点补这个模块的边界和最容易出问题的风险面。"
        if plan.closing_move == "evidence_anchor":
            return "如果需要，我可以继续把指标口径、样本范围和基线一起展开。"
        return "我会把边界先讲清楚，避免把没做过的内容说得过满。"

    def _starter_bullets(self, plan: AnswerPlan) -> list[str]:
        if plan.intent == "tradeoff_reasoning":
            return [
                "先说结论，再补为什么这样取舍",
                "把代价和限制一起说出来",
                "顺手留一个可继续追问的升级点",
            ]
        if plan.intent == "module_deep_dive":
            return [
                "先说模块职责和位置",
                "再说调用链和边界",
                "最后补风险与兜底",
            ]
        if plan.intent == "performance_evidence":
            return [
                "先给结果",
                "补基线和测量口径",
                "再说业务影响",
            ]
        return [
            "先说当前真实做法",
            "再补关键取舍或证据",
            "最后留出升级或边界",
        ]

    def _full_opening(
        self,
        plan: AnswerPlan,
        question: str,
        project_label: str,
        module_label: str,
    ) -> str:
        if plan.opening_move == "responsibility_first":
            return f"先说模块职责，{module_label} 在 {project_label} 里本质上负责承接问题路由和下游分发，所以它天然处在调用链中间。"
        if plan.opening_move == "failure_first":
            return f"先说出过的问题，{project_label}早期最麻烦的是线上不稳定和定位成本高。"
        if plan.opening_move == "limit_first":
            return f"先说当前限制，{project_label}现在最值得继续优化的是复杂度和长尾性能。"
        return f"先说结论，针对“{question}”，{project_label}这边我会先把当前真实做法和关键取舍讲清楚。"

    def _full_detail(
        self,
        plan: AnswerPlan,
        route_reason: str,
        evidence: list[str],
        module_label: str,
    ) -> str:
        evidence_hint = f" 当前能直接落地的证据有：{'、'.join(evidence[:4])}。" if evidence else ""
        route_hint = f" 这道题我会按“{route_reason}”这条线组织。" if route_reason else ""
        if plan.intent == "tradeoff_reasoning":
            return (
                "展开时我会先讲当时有哪些可选方案，再讲为什么最后选了现在这条路径，"
                "最后把付出的代价、已知限制和后续怎么补上说完整。"
                + route_hint
                + evidence_hint
            )
        if plan.intent == "module_deep_dive":
            return (
                f"展开时我会按调用链、边界和风险三层往下讲，重点说明 {module_label} 为什么容易变成瓶颈，"
                "以及它和上下游接口之间最容易出问题的地方。"
                + route_hint
                + evidence_hint
            )
        if plan.intent == "performance_evidence":
            return (
                "展开时我会用指标、基线和测量口径把结论锚住，而不是只说一个好看的结果。"
                + route_hint
                + evidence_hint
            )
        if plan.intent == "failure_analysis":
            return (
                "展开时我会按现象、根因、临时兜底和长期修复来讲，让面试官听得出我是怎么把问题真正收住的。"
                + route_hint
                + evidence_hint
            )
        if plan.intent == "optimization_plan":
            return (
                "展开时我会先讲当前系统最限制效果的点，再讲优先级最高的优化动作和预期影响。"
                + route_hint
                + evidence_hint
            )
        if plan.intent == "architecture_overview":
            return (
                "展开时我会先把层次结构讲清楚，再补关键模块边界、取舍和为什么这样拆。"
                + route_hint
                + evidence_hint
            )
        return (
            "展开时我会先落到真实项目设计，再补证据、边界和升级路线，尽量让回答听起来像现场讲述而不是背稿。"
            + route_hint
            + evidence_hint
        )

    def _full_bullets(self, plan: AnswerPlan, briefing: SessionBriefing, module_label: str) -> list[str]:
        if plan.intent == "module_deep_dive":
            return [
                f"先说 {module_label} 的职责和位置",
                "再说调用链、边界和瓶颈来源",
                "最后补风险面和兜底策略",
                f"保持 {briefing.style_bias[0] if briefing.style_bias else '先结论后展开'}",
            ]
        if plan.intent == "tradeoff_reasoning":
            return [
                "先讲可选方案，再讲为什么这么选",
                "把收益和代价一起交代清楚",
                "最后补已知限制和升级方向",
                f"保持 {briefing.style_bias[0] if briefing.style_bias else '先结论后展开'}",
            ]
        return [
            f"回答风格：{briefing.style_bias[0] if briefing.style_bias else '先结论后展开'}",
            f"重点项目：{', '.join(briefing.priority_projects[:2]) or '通用岗位能力'}",
            f"优先话题：{', '.join(briefing.focus_topics[:3]) or 'agent, latency, evaluation'}",
            "如果被追问，继续下钻到模块职责、指标和代码证据。",
        ]

    def _evidence_ids(self, pack: KnowledgePack) -> list[str]:
        refs = (
            pack.profile_refs
            + pack.retrieval_refs
            + pack.hook_refs
            + pack.evidence_refs
            + pack.project_refs
            + pack.module_refs
            + pack.code_refs
            + pack.role_refs
        )
        return [item.ref_id for item in refs]

    def _evidence_labels(self, pack: KnowledgePack) -> list[str]:
        refs = (
            pack.profile_refs
            + pack.retrieval_refs
            + pack.hook_refs
            + pack.evidence_refs
            + pack.project_refs
            + pack.module_refs
            + pack.code_refs
            + pack.role_refs
        )
        return [item.label for item in refs]


class OpenAIChatProvider:
    """Minimal OpenAI-compatible provider using chat completions over HTTP."""

    def __init__(
        self,
        *,
        endpoint: GenerationLaneSettings,
        prompt_builder: PromptBuilder,
        level: str,
    ) -> None:
        self.endpoint = endpoint
        self.prompt_builder = prompt_builder
        self.level = level

    def starter(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
        stream_state: StarterStreamState | None = None,
    ) -> AnswerDraft:
        return self._generate(
            turn_id=turn_id,
            level="starter",
            question=question,
            route=route,
            pack=pack,
            briefing=briefing,
            candidate_history=candidate_history,
            answer_plan=answer_plan,
            answer_state=answer_state,
            stream_state=stream_state,
        )

    def full(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
    ) -> AnswerDraft:
        return self._generate(
            turn_id=turn_id,
            level="full",
            question=question,
            route=route,
            pack=pack,
            briefing=briefing,
            candidate_history=candidate_history,
            answer_plan=answer_plan,
            answer_state=answer_state,
            stream_state=None,
        )

    def _generate(
        self,
        *,
        turn_id: str,
        level: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None,
        answer_state: AnswerState | None,
        stream_state: StarterStreamState | None,
    ) -> AnswerDraft:
        messages = self.prompt_builder.build_messages(
            level=level,
            question=question,
            route=route,
            pack=pack,
            briefing=briefing,
            candidate_history=candidate_history,
            answer_plan=answer_plan,
            answer_state=answer_state,
        )
        payload = {
            "model": self.endpoint.model,
            "messages": messages,
            "temperature": self.endpoint.temperature,
        }
        if self.endpoint.enable_thinking is not None:
            payload["enable_thinking"] = self.endpoint.enable_thinking
        if level == "starter" and stream_state is not None and self.endpoint.stream_enabled:
            raw_text = self._call_chat_completions_streaming(payload, stream_state)
        else:
            raw_text = self._call_chat_completions(payload)
        parsed = self._parse_json_payload(raw_text)
        bullets = parsed.get("bullets") if isinstance(parsed.get("bullets"), list) else []
        bullets = [str(item) for item in bullets][:4]
        text = str(parsed.get("text") or raw_text).strip()
        return AnswerDraft(
            level=level,
            turn_id=turn_id,
            text=text,
            bullets=bullets,
            evidence_refs=[
                ref.ref_id
                for ref in (
                    pack.profile_refs
                    + pack.retrieval_refs
                    + pack.hook_refs
                    + pack.evidence_refs
                    + pack.project_refs
                    + pack.module_refs
                    + pack.code_refs
                    + pack.role_refs
                )
            ],
        )

    def _call_chat_completions(self, payload: dict) -> str:
        endpoint = f"{self.endpoint.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.endpoint.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "InterviewTrainerDesktop/0.1 (+https://github.com/openai/codex)",
        }
        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.endpoint.request_timeout_s) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - network branch
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM request failed: {exc.code} {detail}") from exc
        except error.URLError as exc:  # pragma: no cover - network branch
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:  # pragma: no cover
            raise RuntimeError(f"Unexpected OpenAI-compatible response shape: {data}") from exc
        if isinstance(content, list):
            joined = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    joined.append(item.get("text", ""))
            return "\n".join(joined).strip()
        return str(content).strip()

    def _call_chat_completions_streaming(self, payload: dict, stream_state: StarterStreamState) -> str:
        endpoint = f"{self.endpoint.base_url}/chat/completions"
        body = json.dumps({**payload, "stream": True}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.endpoint.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "InterviewTrainerDesktop/0.1 (+https://github.com/openai/codex)",
        }
        req = request.Request(endpoint, data=body, headers=headers, method="POST")
        chunks: list[str] = []
        try:
            with request.urlopen(req, timeout=self.endpoint.request_timeout_s) as response:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="ignore").strip()
                    if not decoded or not decoded.startswith("data:"):
                        continue
                    payload_text = decoded[5:].strip()
                    if payload_text == "[DONE]":
                        break
                    try:
                        event = json.loads(payload_text)
                    except json.JSONDecodeError:
                        continue
                    delta = self._extract_stream_delta(event)
                    if not delta:
                        continue
                    chunks.append(delta)
                    raw_text = "".join(chunks)
                    stream_state.ingest(raw_text, parsed_text=self._extract_partial_text(raw_text))
        except error.HTTPError as exc:  # pragma: no cover - network branch
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM request failed: {exc.code} {detail}") from exc
        except error.URLError as exc:  # pragma: no cover - network branch
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc
        return "".join(chunks).strip()

    @staticmethod
    def _extract_stream_delta(event: dict) -> str:
        try:
            delta = event["choices"][0]["delta"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
        if isinstance(delta, list):
            parts = []
            for item in delta:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
            return "".join(parts)
        return str(delta or "")

    def _parse_json_payload(self, raw_text: str) -> dict:
        raw_text = raw_text.strip()
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(raw_text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return {"text": raw_text, "bullets": []}

    def _extract_partial_text(self, raw_text: str) -> str:
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            text_value = parsed.get("text")
            if isinstance(text_value, str) and text_value.strip():
                return text_value.strip()

        marker_index = raw_text.find('"text"')
        if marker_index == -1:
            return ""
        colon_index = raw_text.find(":", marker_index)
        if colon_index == -1:
            return ""
        quote_index = raw_text.find('"', colon_index)
        if quote_index == -1:
            return ""

        escaped = False
        fragments: list[str] = []
        for current in raw_text[quote_index + 1 :]:
            if escaped:
                fragments.append(current)
                escaped = False
                continue
            if current == "\\":
                escaped = True
                continue
            if current == '"':
                return self._decode_json_fragment("".join(fragments))
            fragments.append(current)
        return self._decode_json_fragment("".join(fragments))

    @staticmethod
    def _decode_json_fragment(fragment: str) -> str:
        return (
            fragment
            .replace("\\n", "\n")
            .replace("\\r", "")
            .replace("\\t", "\t")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        ).strip()


class DualDraftComposer:
    def __init__(
        self,
        fast_provider: LLMProvider,
        smart_provider: LLMProvider,
        *,
        max_workers: int = 4,
    ) -> None:
        self.fast_provider = fast_provider
        self.smart_provider = smart_provider
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="draft-composer")

    def shutdown(self, *, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def start(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        knowledge: CompiledKnowledge,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
    ) -> DraftFutures:
        del knowledge
        starter_stream_state = StarterStreamState()
        common = {
            "turn_id": turn_id,
            "question": question,
            "route": route,
            "pack": pack,
            "briefing": briefing,
            "candidate_history": candidate_history,
            "answer_plan": answer_plan,
            "answer_state": answer_state,
        }
        return DraftFutures(
            turn_id=turn_id,
            starter_future=self._executor.submit(
                self._timed_call,
                self.fast_provider.starter,
                **common,
                stream_state=starter_stream_state,
            ),
            full_future=self._executor.submit(self._timed_call, self.smart_provider.full, **common),
            started_at=time.perf_counter(),
            starter_stream_state=starter_stream_state,
        )

    def start_starter_prewarm(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        knowledge: CompiledKnowledge,
        briefing: SessionBriefing,
        candidate_history: list[str],
    ) -> StarterPrewarm:
        del knowledge
        starter_stream_state = StarterStreamState()
        common = {
            "turn_id": turn_id,
            "question": question,
            "route": route,
            "pack": pack,
            "briefing": briefing,
            "candidate_history": candidate_history,
        }
        return StarterPrewarm(
            turn_id=turn_id,
            question=question,
            starter_future=self._executor.submit(
                self._timed_call,
                self.fast_provider.starter,
                **common,
                stream_state=starter_stream_state,
            ),
            started_at=time.perf_counter(),
            starter_stream_state=starter_stream_state,
        )

    def start_with_existing_starter(
        self,
        *,
        prewarm: StarterPrewarm,
        route: ContextRoute,
        pack: KnowledgePack,
        knowledge: CompiledKnowledge,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
    ) -> DraftFutures:
        del knowledge
        return DraftFutures(
            turn_id=prewarm.turn_id,
            starter_future=prewarm.starter_future,
            full_future=self._executor.submit(
                self._timed_call,
                self.smart_provider.full,
                turn_id=prewarm.turn_id,
                question=prewarm.question,
                route=route,
                pack=pack,
                briefing=briefing,
                candidate_history=candidate_history,
                answer_plan=answer_plan,
                answer_state=answer_state,
            ),
            started_at=prewarm.started_at,
            starter_stream_state=prewarm.starter_stream_state,
        )

    def collect_ready(self, futures: DraftFutures) -> dict[str, DraftOutcome]:
        ready: dict[str, DraftOutcome] = {}
        if futures.starter_future.done() and futures.starter_future.exception() is None:
            ready["starter"] = futures.starter_future.result()
        if futures.full_future.done() and futures.full_future.exception() is None:
            ready["full"] = futures.full_future.result()
        return ready

    def compose(
        self,
        *,
        turn_id: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        knowledge: CompiledKnowledge,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
    ) -> dict[str, AnswerDraft]:
        futures = self.start(
            turn_id=turn_id,
            question=question,
            route=route,
            pack=pack,
            knowledge=knowledge,
            briefing=briefing,
            candidate_history=candidate_history,
            answer_plan=answer_plan,
            answer_state=answer_state,
        )
        starter = futures.starter_future.result().draft
        full = futures.full_future.result().draft
        return {"starter": starter, "full": full}

    def _timed_call(self, func, **kwargs) -> DraftOutcome:
        started = time.perf_counter()
        draft = func(**kwargs)
        return DraftOutcome(
            draft=draft,
            latency_ms=(time.perf_counter() - started) * 1000,
        )


def build_dual_draft_composer(settings: GenerationSettings | None = None) -> DualDraftComposer:
    settings = settings or GenerationSettings.from_env()
    prompt_builder = PromptBuilder()
    fast_lane = settings.fast_lane
    smart_lane = settings.smart_lane
    return DualDraftComposer(
        fast_provider=(
            OpenAIChatProvider(
                endpoint=fast_lane,
                prompt_builder=prompt_builder,
                level="starter",
            )
            if fast_lane.use_openai
            else TemplateLLMProvider("fast")
        ),
        smart_provider=(
            OpenAIChatProvider(
                endpoint=smart_lane,
                prompt_builder=prompt_builder,
                level="full",
            )
            if smart_lane.use_openai
            else TemplateLLMProvider("smart")
        ),
    )
