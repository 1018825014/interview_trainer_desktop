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
        focus = self._focus_phrase(pack, briefing)
        history_hint = ""
        if candidate_history:
            history_hint = f" 我会承接我刚才已经说过的内容，先别把话题跳丢。"
        text = (
            f"这个问题我会先从{focus}说起。"
            f"{history_hint}先给结论：我会用真实实现、关键取舍和升级路线来回答。"
        )
        bullets = [
            "先说当时真实做了什么",
            "再说为什么这样取舍",
            "最后补限制和升级方向",
        ]
        return AnswerDraft(
            level="starter",
            turn_id=turn_id,
            text=text,
            bullets=bullets,
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
        evidence = self._evidence_labels(pack)
        route_reason = route.reason.rstrip("。！？!? ")
        frame = (
            f"先讲结论。针对“{question}”，"
            f"我会优先从真实实现切入，这道题当前更适合按“{route_reason}”来组织回答。"
        )
        if pack.project_refs:
            frame += " 我会先把答案落到项目证据上，比如 " + "、".join(
                ref.label for ref in pack.project_refs[:2]
            ) + "。"
        if candidate_history:
            frame += f" 同时我会承接我刚才已经说过的内容，比如“{candidate_history[-1][:80]}”。"

        deep_dive = (
            "展开时我会按四层来讲："
            "第一层是业务目标和成功指标，"
            "第二层是当前真实架构和关键模块边界，"
            "第三层是为什么没有一开始就上更复杂的方案，"
            "第四层是已知限制、失败案例和下一步升级。"
        )
        if evidence:
            deep_dive += f" 当前可直接引用的证据包括：{'、'.join(evidence[:5])}。"

        bullets = [
            f"回答风格：{briefing.style_bias[0]}",
            f"重点项目：{', '.join(briefing.priority_projects[:2]) or '通用岗位能力'}",
            f"优先话题：{', '.join(briefing.focus_topics[:3]) or 'agent, latency, evaluation'}",
            "如果被追问，我会继续下钻到模块职责、指标和代码证据。",
        ]
        return AnswerDraft(
            level="full",
            turn_id=turn_id,
            text=f"{frame} {deep_dive}",
            bullets=bullets,
            evidence_refs=self._evidence_ids(pack),
        )

    def _focus_phrase(self, pack: KnowledgePack, briefing: SessionBriefing) -> str:
        if pack.project_refs:
            return f"{pack.project_refs[0].label} 这个项目的真实取舍"
        if pack.role_refs:
            return f"{briefing.company or '这个岗位'}更看重的能力点"
        return "业务目标和落地取舍"

    def _evidence_ids(self, pack: KnowledgePack) -> list[str]:
        refs = pack.profile_refs + pack.project_refs + pack.module_refs + pack.code_refs + pack.role_refs
        return [item.ref_id for item in refs]

    def _evidence_labels(self, pack: KnowledgePack) -> list[str]:
        refs = pack.profile_refs + pack.project_refs + pack.module_refs + pack.code_refs + pack.role_refs
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
