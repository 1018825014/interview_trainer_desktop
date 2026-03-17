from __future__ import annotations

from .answer_control import AnswerPlan, AnswerState
from .types import ContextRoute, KnowledgePack, SessionBriefing


class PromptBuilder:
    def build_messages(
        self,
        *,
        level: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None = None,
        answer_state: AnswerState | None = None,
    ) -> list[dict[str, str]]:
        system = self._system_prompt(level)
        user = self._user_prompt(
            level=level,
            question=question,
            route=route,
            pack=pack,
            briefing=briefing,
            candidate_history=candidate_history,
            answer_plan=answer_plan,
            answer_state=answer_state,
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _system_prompt(self, level: str) -> str:
        base = (
            "You are an interview answer coach for mock interviews. "
            "Always answer like a strong candidate speaking naturally, not like a textbook. "
            "Never fabricate that the candidate has already implemented something if the evidence does not support it. "
            "Prefer: real implementation -> why that tradeoff was chosen -> known limitations -> upgrade path. "
            "Return strict JSON only with keys 'text' and 'bullets'. "
            "The 'text' value must be a spoken answer in natural Chinese. "
            "The 'bullets' value must be an array of short Chinese bullet strings."
        )
        if level == "starter":
            return (
                base
                + " Keep the text to 1-2 spoken sentences so the candidate can start talking immediately. "
                + "Bullets should be 2-3 compact speaking cues."
            )
        return (
            base
            + " For the full answer, provide a more complete spoken response that can survive 1-2 follow-up questions. "
            + "Bullets should be 3-4 high-signal talking points."
        )

    def _user_prompt(
        self,
        *,
        level: str,
        question: str,
        route: ContextRoute,
        pack: KnowledgePack,
        briefing: SessionBriefing,
        candidate_history: list[str],
        answer_plan: AnswerPlan | None,
        answer_state: AnswerState | None,
    ) -> str:
        candidate_context = candidate_history[-3:] if candidate_history else []
        return "\n".join(
            [
                f"Question: {question}",
                f"Route: {route.mode.value}",
                f"Route reason: {route.reason}",
                f"Level: {level}",
                f"Company: {briefing.company or 'N/A'}",
                f"Business context: {briefing.business_context or 'N/A'}",
                f"JD focus topics: {', '.join(briefing.focus_topics) or 'N/A'}",
                f"Priority projects: {', '.join(briefing.priority_projects) or 'N/A'}",
                f"Style bias: {', '.join(briefing.style_bias)}",
                f"Intent: {answer_plan.intent if answer_plan else 'N/A'}",
                f"Retrieve priority: {', '.join(answer_plan.retrieve_priority) if answer_plan else 'N/A'}",
                f"Answer template: {', '.join(answer_plan.answer_template) if answer_plan else 'N/A'}",
                f"Need metrics: {answer_plan.need_metrics if answer_plan else False}",
                f"Need code evidence: {answer_plan.need_code_evidence if answer_plan else False}",
                f"Allow hook: {answer_plan.allow_hook if answer_plan else False}",
                f"Active project id: {answer_state.active_project_id if answer_state else 'N/A'}",
                f"Active module id: {answer_state.active_module_id if answer_state else 'N/A'}",
                f"Follow-up thread: {answer_state.followup_thread if answer_state else 'N/A'}",
                f"Used hook ids: {', '.join(answer_state.used_hook_ids) if answer_state and answer_state.used_hook_ids else 'none'}",
                "Candidate already said:",
                *([f"- {item}" for item in candidate_context] or ["- nothing yet"]),
                "Evidence pack:",
                *self._format_pack(pack),
                (
                    "Important: if the question is about the candidate's own project, make the answer feel grounded in the real project. "
                    "If the evidence is incomplete, state the current real design first and then present a reasonable upgrade path."
                ),
            ]
        )

    def _format_pack(self, pack: KnowledgePack) -> list[str]:
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
        if not refs:
            return ["- no extra evidence"]
        return [f"- [{ref.kind}] {ref.label}: {ref.snippet}" for ref in refs]
