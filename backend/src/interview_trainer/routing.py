from __future__ import annotations

from typing import Iterable

from .answer_control import AnswerPlan
from .library_retriever import LibraryRetriever

from .types import (
    CompiledKnowledge,
    ContextMode,
    ContextRoute,
    EvidenceRef,
    KnowledgePack,
    ProjectInterviewPack,
    SessionBriefing,
)

from .library_types import CompiledBundlePayload


PROJECT_KEYWORDS = {
    "项目",
    "架构",
    "模块",
    "实现",
    "为什么这样设计",
    "上线",
    "性能",
    "延迟",
    "成本",
    "失败",
    "取舍",
}

PROJECT_KEYWORDS.update(
    {
        "project",
        "architecture",
        "module",
        "implementation",
        "tradeoff",
        "performance",
        "failure",
    }
)


ROLE_KEYWORDS = {
    "agent",
    "rag",
    "tool",
    "workflow",
    "prompt",
    "evaluation",
    "评测",
    "缓存",
    "trace",
    "guardrail",
    "latency",
    "cost",
    "观测",
    "工具调用",
}


CODE_DETAIL_KEYWORDS = {"代码", "函数", "类", "接口", "实现", "模块", "缓存", "检索", "工作流"}


class ContextRouter:
    def __init__(self, retriever: LibraryRetriever | None = None) -> None:
        self.retriever = retriever or LibraryRetriever()

    def route(
        self,
        question: str,
        knowledge: CompiledKnowledge,
        briefing: SessionBriefing | None = None,
    ) -> ContextRoute:
        normalized = question.lower()
        project_match = self._matches_project(question, knowledge.projects)
        role_haystack = normalized
        if project_match:
            role_haystack = role_haystack.replace(project_match.name.lower(), " ")
            for module in project_match.key_modules:
                role_haystack = role_haystack.replace(module.name.lower(), " ")
        looks_like_project = project_match is not None or any(keyword in question for keyword in PROJECT_KEYWORDS)
        looks_like_role = any(keyword in role_haystack for keyword in ROLE_KEYWORDS)

        if briefing and any(topic.lower() in role_haystack for topic in briefing.focus_topics):
            looks_like_role = True

        if looks_like_project and looks_like_role:
            return ContextRoute(
                mode=ContextMode.HYBRID,
                reason="问题既指向你的真实项目，又涉及岗位方法论或大模型系统设计。",
            )
        if looks_like_project:
            return ContextRoute(
                mode=ContextMode.PROJECT,
                reason="问题主要在追问你的项目实现、取舍、指标或失败案例。",
            )
        if looks_like_role:
            return ContextRoute(
                mode=ContextMode.ROLE,
                reason="问题主要是 AI Agent / LLM 应用开发岗位的通用深问。",
            )
        return ContextRoute(
            mode=ContextMode.GENERIC,
            reason="问题更像通用表达题或常规行为面问题，少量上下文即可回答。",
        )

    def build_pack(
        self,
        question: str,
        route: ContextRoute,
        knowledge: CompiledKnowledge,
        answer_plan: AnswerPlan | None = None,
    ) -> KnowledgePack:
        project_refs: list[EvidenceRef] = []
        module_refs: list[EvidenceRef] = []
        code_refs: list[EvidenceRef] = []
        role_refs: list[EvidenceRef] = []

        project = self._matches_project(question, knowledge.projects) or (knowledge.projects[0] if knowledge.projects else None)
        if project and route.mode in {ContextMode.PROJECT, ContextMode.HYBRID}:
            project_refs.append(
                EvidenceRef(
                    ref_id=project.project_id,
                    label=project.name,
                    kind="project",
                    snippet=project.pitch_90,
                )
            )
            module_refs.extend(self._match_modules(question, project))
            if self._should_include_code(question, answer_plan):
                code_refs.extend(self._match_code(question, project))

        if route.mode in {ContextMode.ROLE, ContextMode.HYBRID, ContextMode.GENERIC}:
            for playbook in knowledge.role_playbooks[:2]:
                role_refs.append(
                    EvidenceRef(
                        ref_id=playbook.playbook_id,
                        label=playbook.role_name,
                        kind="role",
                        snippet=" / ".join(playbook.focus_areas[:4]),
                    )
                )

        profile_refs = [
            EvidenceRef(
                ref_id="profile",
                label="Candidate Profile",
                kind="profile",
                snippet=knowledge.profile_card.headline,
            )
        ]

        return KnowledgePack(
            profile_refs=profile_refs,
            retrieval_refs=[],
            evidence_refs=[],
            project_refs=project_refs,
            module_refs=module_refs,
            code_refs=code_refs[:3],
            role_refs=role_refs[:3],
        )

    def build_pack_for_plan(
        self,
        *,
        question: str,
        plan: AnswerPlan,
        compiled_bundle: CompiledBundlePayload,
        route: ContextRoute | None = None,
        briefing: SessionBriefing | None = None,
    ) -> KnowledgePack:
        selection = self.retriever.retrieve(
            question=question,
            plan=plan,
            bundle=compiled_bundle,
        )
        role_refs: list[EvidenceRef] = []
        route_mode = route.mode if route is not None else ContextMode.PROJECT
        if route_mode in {ContextMode.ROLE, ContextMode.HYBRID, ContextMode.GENERIC}:
            for playbook in compiled_bundle.compiled_knowledge.role_playbooks[:2]:
                role_refs.append(
                    EvidenceRef(
                        ref_id=playbook.playbook_id,
                        label=playbook.role_name,
                        kind="role",
                        snippet=" / ".join(playbook.focus_areas[:4]),
                    )
                )
        profile_refs = [
            EvidenceRef(
                ref_id="profile",
                label="Candidate Profile",
                kind="profile",
                snippet=compiled_bundle.compiled_knowledge.profile_card.headline,
            )
        ]
        del briefing
        return KnowledgePack(
            profile_refs=profile_refs,
            retrieval_refs=selection.retrieval_refs,
            evidence_refs=selection.evidence_refs,
            project_refs=selection.project_refs,
            module_refs=selection.module_refs,
            code_refs=selection.code_refs,
            role_refs=role_refs[:2],
        )

    def _should_include_code(self, question: str, answer_plan: AnswerPlan | None) -> bool:
        if answer_plan and answer_plan.need_code_evidence:
            return True
        return self._looks_like_code_detail(question)

    def _matches_project(self, question: str, projects: Iterable[ProjectInterviewPack]) -> ProjectInterviewPack | None:
        normalized = question.lower()
        for project in projects:
            if project.name.lower() in normalized:
                return project
            if any(module.name.lower() in normalized for module in project.key_modules):
                return project
        return None

    def _match_modules(self, question: str, project: ProjectInterviewPack) -> list[EvidenceRef]:
        normalized = question.lower()
        refs = []
        for module in project.key_modules:
            if module.name.lower() in normalized or any(keyword in normalized for keyword in module.interfaces):
                refs.append(
                    EvidenceRef(
                        ref_id=module.module_id,
                        label=module.name,
                        kind="module",
                        snippet=module.responsibility,
                    )
                )
        if not refs:
            refs.extend(
                EvidenceRef(
                    ref_id=module.module_id,
                    label=module.name,
                    kind="module",
                    snippet=module.responsibility,
                )
                for module in project.key_modules[:2]
            )
        return refs

    def _match_code(self, question: str, project: ProjectInterviewPack) -> list[EvidenceRef]:
        normalized = question.lower()
        refs = []
        for chunk in project.code_chunks:
            if any(keyword in normalized for keyword in chunk.keywords) or chunk.path.lower().split("/")[-1] in normalized:
                refs.append(
                    EvidenceRef(
                        ref_id=chunk.chunk_id,
                        label=chunk.path,
                        kind="code",
                        snippet=chunk.summary,
                    )
                )
        if not refs:
            refs.extend(
                EvidenceRef(
                    ref_id=chunk.chunk_id,
                    label=chunk.path,
                    kind="code",
                    snippet=chunk.summary,
                )
                for chunk in project.code_chunks[:2]
            )
        return refs

    def _looks_like_code_detail(self, question: str) -> bool:
        normalized = question.lower()
        return any(keyword in normalized for keyword in CODE_DETAIL_KEYWORDS)
