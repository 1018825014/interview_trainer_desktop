from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


_TRADEOFF_KEYWORDS = {
    "为什么",
    "取舍",
    "tradeoff",
    "而不是",
    "为什么不用",
    "一体化",
    "all-in-one",
}
_MODULE_KEYWORDS = {
    "模块",
    "函数",
    "类",
    "接口",
    "实现",
    "代码",
    "瓶颈",
    "调用链",
    "上下游",
}
_PERFORMANCE_KEYWORDS = {
    "延迟",
    "latency",
    "性能",
    "benchmark",
    "指标",
    "测量",
    "命中率",
    "吞吐",
}
_FAILURE_KEYWORDS = {
    "失败",
    "故障",
    "风险",
    "bug",
    "事故",
    "兜底",
    "稳定",
}
_OPTIMIZATION_KEYWORDS = {
    "优化",
    "升级",
    "重做",
    "未来",
    "下一步",
    "怎么改",
}
_ARCHITECTURE_KEYWORDS = {
    "架构",
    "设计",
    "整体",
    "系统",
    "architecture",
    "structure",
}
_PROJECT_INTRO_KEYWORDS = {
    "介绍",
    "讲讲",
    "是什么",
    "做什么",
    "项目",
    "project",
}


@dataclass(slots=True)
class AnswerPlan:
    intent: str
    retrieve_priority: list[str]
    answer_template: list[str]
    max_sentences: int
    need_metrics: bool
    need_code_evidence: bool
    allow_hook: bool
    preferred_hook_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AnswerState:
    active_project_id: str | None = None
    active_module_id: str | None = None
    spoken_claims: list[str] = field(default_factory=list)
    used_hook_ids: list[str] = field(default_factory=list)
    followup_thread: str = ""


class AnswerController:
    def build_plan(
        self,
        *,
        question: str,
        route_mode: str,
        active_project_ids: list[str],
        active_module_ids: list[str] | None = None,
        previous_state: AnswerState | None = None,
    ) -> AnswerPlan:
        intent = self._classify_intent(
            question=question,
            route_mode=route_mode,
            active_project_ids=active_project_ids,
            active_module_ids=active_module_ids or [],
            previous_state=previous_state,
        )
        retrieve_priority = self._retrieve_priority(intent)
        answer_template = self._answer_template(intent)
        need_metrics = intent in {"performance_evidence", "tradeoff_reasoning", "optimization_plan"}
        need_code_evidence = intent in {"module_deep_dive", "architecture_overview"}
        allow_hook = intent in {
            "project_intro",
            "architecture_overview",
            "tradeoff_reasoning",
            "optimization_plan",
        }
        max_sentences = 4 if intent in {"project_intro", "architecture_overview"} else 6
        preferred_hook_ids = active_project_ids[:1] if allow_hook else []
        return AnswerPlan(
            intent=intent,
            retrieve_priority=retrieve_priority,
            answer_template=answer_template,
            max_sentences=max_sentences,
            need_metrics=need_metrics,
            need_code_evidence=need_code_evidence,
            allow_hook=allow_hook,
            preferred_hook_ids=preferred_hook_ids,
        )

    def advance_state(
        self,
        *,
        previous_state: AnswerState | None,
        plan: AnswerPlan,
        active_project_ids: list[str],
        active_module_ids: list[str],
        question: str,
    ) -> AnswerState:
        previous = previous_state or AnswerState()
        active_project_id = active_project_ids[0] if active_project_ids else previous.active_project_id
        active_module_id = active_module_ids[0] if active_module_ids else previous.active_module_id
        spoken_claims = list(previous.spoken_claims)
        snippet = _clean_text(question)[:120]
        if snippet and snippet not in spoken_claims:
            spoken_claims.append(snippet)
        return AnswerState(
            active_project_id=active_project_id,
            active_module_id=active_module_id if plan.intent == "module_deep_dive" else None,
            spoken_claims=spoken_claims[-6:],
            used_hook_ids=list(previous.used_hook_ids),
            followup_thread=plan.intent,
        )

    def _classify_intent(
        self,
        *,
        question: str,
        route_mode: str,
        active_project_ids: list[str],
        active_module_ids: list[str],
        previous_state: AnswerState | None,
    ) -> str:
        normalized = _clean_text(question).lower()
        if any(keyword in normalized for keyword in _PERFORMANCE_KEYWORDS):
            return "performance_evidence"
        if any(keyword in normalized for keyword in _FAILURE_KEYWORDS):
            return "failure_analysis"
        if any(keyword in normalized for keyword in _OPTIMIZATION_KEYWORDS):
            return "optimization_plan"
        if any(keyword in normalized for keyword in _MODULE_KEYWORDS):
            return "module_deep_dive"
        if any(keyword in normalized for keyword in _TRADEOFF_KEYWORDS):
            return "tradeoff_reasoning"
        if any(keyword in normalized for keyword in _ARCHITECTURE_KEYWORDS):
            return "architecture_overview"
        if route_mode == "project" and (
            active_project_ids or any(keyword in normalized for keyword in _PROJECT_INTRO_KEYWORDS)
        ):
            return "project_intro"
        if route_mode == "role":
            return "role_fit"
        if previous_state and previous_state.followup_thread and active_project_ids:
            return previous_state.followup_thread
        return "generic_behavior"

    def _retrieve_priority(self, intent: str) -> list[str]:
        if intent == "module_deep_dive":
            return ["RetrievalUnit", "ModuleCardPlus", "CodeChunk", "EvidenceCard"]
        if intent == "performance_evidence":
            return ["RetrievalUnit", "MetricEvidence", "EvidenceCard", "Project"]
        if intent == "tradeoff_reasoning":
            return ["RetrievalUnit", "Project", "EvidenceCard", "ModuleCardPlus"]
        if intent == "architecture_overview":
            return ["RetrievalUnit", "Project", "ModuleCardPlus", "RepoMap"]
        if intent == "optimization_plan":
            return ["RetrievalUnit", "Project", "MetricEvidence", "EvidenceCard"]
        if intent == "failure_analysis":
            return ["RetrievalUnit", "EvidenceCard", "ModuleCardPlus", "Project"]
        if intent == "project_intro":
            return ["RetrievalUnit", "Project", "EvidenceCard"]
        return ["RetrievalUnit", "Project", "RolePlaybook"]

    def _answer_template(self, intent: str) -> list[str]:
        if intent == "tradeoff_reasoning":
            return ["context", "options", "choice", "reason", "cost"]
        if intent == "performance_evidence":
            return ["conclusion", "metric", "method", "impact"]
        if intent == "module_deep_dive":
            return ["module_role", "call_path", "boundary", "risk"]
        if intent == "failure_analysis":
            return ["failure_case", "root_cause", "mitigation", "learning"]
        if intent == "optimization_plan":
            return ["current_limit", "priority_fix", "expected_impact", "next_step"]
        if intent == "architecture_overview":
            return ["goal", "layers", "key_modules", "tradeoff"]
        if intent == "project_intro":
            return ["goal", "solution", "result", "hook"]
        return ["conclusion", "evidence", "boundary"]
