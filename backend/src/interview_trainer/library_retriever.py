from __future__ import annotations

from dataclasses import dataclass, field

from .answer_control import AnswerPlan, AnswerState
from .library_types import CompiledBundlePayload, MetricEvidence, RetrievalUnit
from .types import EvidenceRef, ProjectInterviewPack


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe_refs(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    seen: set[str] = set()
    deduped: list[EvidenceRef] = []
    for ref in refs:
        token = f"{ref.kind}:{ref.ref_id}"
        if token in seen:
            continue
        seen.add(token)
        deduped.append(ref)
    return deduped


@dataclass(slots=True)
class RetrievalSelection:
    retrieval_refs: list[EvidenceRef] = field(default_factory=list)
    hook_refs: list[EvidenceRef] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    project_refs: list[EvidenceRef] = field(default_factory=list)
    module_refs: list[EvidenceRef] = field(default_factory=list)
    code_refs: list[EvidenceRef] = field(default_factory=list)


class LibraryRetriever:
    def retrieve(
        self,
        *,
        question: str,
        plan: AnswerPlan,
        bundle: CompiledBundlePayload,
        answer_state: AnswerState | None = None,
    ) -> RetrievalSelection:
        matched_units = self._match_units(question=question, plan=plan, bundle=bundle, answer_state=answer_state)
        selected_projects = self._select_projects(question=question, units=matched_units, bundle=bundle)
        retrieval_refs = [
            EvidenceRef(
                ref_id=unit.unit_id,
                label=self._unit_label(unit, bundle),
                kind="retrieval",
                snippet=unit.short_answer,
            )
            for unit in matched_units
        ]
        hook_refs = self._collect_hook_refs(plan=plan, units=matched_units, answer_state=answer_state)
        evidence_refs = self._collect_evidence_refs(plan=plan, units=matched_units, bundle=bundle)
        project_refs = [
            EvidenceRef(
                ref_id=project.project_id,
                label=project.name,
                kind="project",
                snippet=project.pitch_90 or project.pitch_30,
            )
            for project in selected_projects
        ]
        module_refs = self._collect_module_refs(units=matched_units, selected_projects=selected_projects, bundle=bundle)
        code_refs = self._collect_code_refs(
            plan=plan,
            units=matched_units,
            selected_projects=selected_projects,
            bundle=bundle,
        )
        return RetrievalSelection(
            retrieval_refs=_dedupe_refs(retrieval_refs[:3]),
            hook_refs=_dedupe_refs(hook_refs[:1]),
            evidence_refs=_dedupe_refs(evidence_refs[:4]),
            project_refs=_dedupe_refs(project_refs[:2]),
            module_refs=_dedupe_refs(module_refs[:3]),
            code_refs=_dedupe_refs(code_refs[: 2 if plan.need_code_evidence else 1]),
        )

    def _match_units(
        self,
        *,
        question: str,
        plan: AnswerPlan,
        bundle: CompiledBundlePayload,
        answer_state: AnswerState | None,
    ) -> list[RetrievalUnit]:
        normalized = question.lower()
        used_hook_ids = set(answer_state.used_hook_ids) if answer_state else set()
        scored: list[tuple[int, RetrievalUnit]] = []
        for unit in bundle.retrieval_units:
            score = 0
            if unit.unit_type == plan.intent:
                score += 6
            if any(form.lower() in normalized for form in unit.question_forms):
                score += 4
            if any(point.lower() in normalized for point in unit.key_points if point):
                score += 2
            if any(claim.lower() in normalized for claim in unit.safe_claims if claim):
                score += 1
            if plan.allow_hook and unit.hooks:
                score += 2
                score += 3 if unit.unit_id not in used_hook_ids else -3
            if score > 0:
                scored.append((score, unit))
        if not scored:
            scored = [
                (1, unit)
                for unit in bundle.retrieval_units
                if unit.unit_type == plan.intent
            ]
        if not scored:
            scored = [(1, unit) for unit in bundle.retrieval_units[:2]]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [unit for _, unit in scored[:3]]

    def _collect_hook_refs(
        self,
        *,
        plan: AnswerPlan,
        units: list[RetrievalUnit],
        answer_state: AnswerState | None,
    ) -> list[EvidenceRef]:
        if not plan.allow_hook:
            return []
        used_hook_ids = set(answer_state.used_hook_ids) if answer_state else set()
        refs: list[EvidenceRef] = []
        for unit in units:
            if not unit.hooks:
                continue
            if unit.unit_id in used_hook_ids:
                continue
            refs.append(
                EvidenceRef(
                    ref_id=unit.unit_id,
                    label=unit.hooks[0],
                    kind="hook",
                    snippet="unused hook",
                )
            )
        if refs:
            return refs
        for unit in units:
            if unit.hooks:
                return [
                    EvidenceRef(
                        ref_id=unit.unit_id,
                        label=unit.hooks[0],
                        kind="hook",
                        snippet="reused hook",
                    )
                ]
        return []

    def _select_projects(
        self,
        *,
        question: str,
        units: list[RetrievalUnit],
        bundle: CompiledBundlePayload,
    ) -> list[ProjectInterviewPack]:
        project_ids = [unit.project_id for unit in units if _clean_text(unit.project_id)]
        if not project_ids:
            normalized = question.lower()
            for project in bundle.compiled_knowledge.projects:
                if project.name.lower() in normalized:
                    project_ids.append(project.project_id)
                    break
        if not project_ids and bundle.compiled_knowledge.projects:
            project_ids.append(bundle.compiled_knowledge.projects[0].project_id)
        return [
            project
            for project in bundle.compiled_knowledge.projects
            if project.project_id in project_ids
        ]

    def _collect_evidence_refs(
        self,
        *,
        plan: AnswerPlan,
        units: list[RetrievalUnit],
        bundle: CompiledBundlePayload,
    ) -> list[EvidenceRef]:
        refs: list[EvidenceRef] = []
        support_ids = [support_id for unit in units for support_id in unit.supporting_refs]
        evidence_by_id = {item.evidence_id: item for item in bundle.evidence_cards}
        metric_by_id = {item.evidence_id: item for item in bundle.metric_evidence}
        for support_id in support_ids:
            if support_id in metric_by_id:
                metric = metric_by_id[support_id]
                refs.append(self._metric_ref(metric))
            elif support_id in evidence_by_id:
                evidence = evidence_by_id[support_id]
                refs.append(
                    EvidenceRef(
                        ref_id=evidence.evidence_id,
                        label=evidence.title,
                        kind="evidence",
                        snippet=evidence.summary,
                    )
                )
        if plan.need_metrics:
            refs.extend(self._metric_ref(metric) for metric in bundle.metric_evidence[:2])
        return refs

    def _collect_module_refs(
        self,
        *,
        units: list[RetrievalUnit],
        selected_projects: list[ProjectInterviewPack],
        bundle: CompiledBundlePayload,
    ) -> list[EvidenceRef]:
        module_ids = [unit.module_id for unit in units if _clean_text(unit.module_id)]
        if not module_ids:
            module_ids = [
                module.module_id
                for module in bundle.module_cards
                if any(project.project_id == module.project_id for project in selected_projects)
            ]
        refs: list[EvidenceRef] = []
        for module in bundle.module_cards:
            if module.module_id in module_ids:
                refs.append(
                    EvidenceRef(
                        ref_id=module.module_id,
                        label=module.name,
                        kind="module",
                        snippet=module.responsibility,
                    )
                )
        return refs

    def _collect_code_refs(
        self,
        *,
        plan: AnswerPlan,
        units: list[RetrievalUnit],
        selected_projects: list[ProjectInterviewPack],
        bundle: CompiledBundlePayload,
    ) -> list[EvidenceRef]:
        if "CodeChunk" not in plan.retrieve_priority and not plan.need_code_evidence:
            return []
        preferred_module_ids = [unit.module_id for unit in units if _clean_text(unit.module_id)]
        refs: list[EvidenceRef] = []
        for project in selected_projects:
            for chunk in project.code_chunks:
                if preferred_module_ids and chunk.module_id not in preferred_module_ids:
                    continue
                refs.append(
                    EvidenceRef(
                        ref_id=chunk.chunk_id,
                        label=chunk.path,
                        kind="code",
                        snippet=chunk.summary,
                    )
                )
        if not refs and selected_projects:
            refs = [
                EvidenceRef(
                    ref_id=chunk.chunk_id,
                    label=chunk.path,
                    kind="code",
                    snippet=chunk.summary,
                )
                for chunk in selected_projects[0].code_chunks[:2]
            ]
        return refs

    def _metric_ref(self, metric: MetricEvidence) -> EvidenceRef:
        return EvidenceRef(
            ref_id=metric.evidence_id,
            label=metric.metric_name,
            kind="evidence",
            snippet=f"{metric.baseline} -> {metric.metric_value}",
        )

    def _unit_label(self, unit: RetrievalUnit, bundle: CompiledBundlePayload) -> str:
        project_name = next(
            (
                project.name
                for project in bundle.compiled_knowledge.projects
                if project.project_id == unit.project_id
            ),
            unit.project_id,
        )
        return f"{project_name} / {unit.unit_type}"
