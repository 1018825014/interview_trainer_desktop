from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from .knowledge import KnowledgeCompiler, _slugify
from .library_types import (
    CompiledBundlePayload,
    EvidenceCard,
    MetricEvidence,
    ModuleCardPlus,
    RetrievalUnit,
)
from .types import CodeChunk, ProjectInterviewPack


_METRIC_FROM_TO_PATTERN = re.compile(
    r"(?P<name>latency|response\s*time|throughput|accuracy|recall|precision|cost|time)"
    r"[^.\n]{0,80}?"
    r"from\s+(?P<baseline>\d+(?:\.\d+)?\s*(?:ms|s|%|x|qps|rps))"
    r"\s+to\s+(?P<value>\d+(?:\.\d+)?\s*(?:ms|s|%|x|qps|rps))",
    re.IGNORECASE,
)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        clean = _clean_text(item)
        if clean and clean not in deduped:
            deduped.append(clean)
    return deduped


def _dedupe_by_key(items: list[Any], key_fn: Any) -> list[Any]:
    deduped: list[Any] = []
    seen: set[str] = set()
    for item in items:
        key = _clean_text(key_fn(item))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _project_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in payload.get("projects", [])
        if isinstance(item, dict)
    ]


def _normalize_metric_name(raw_name: str) -> str:
    lowered = _clean_text(raw_name).lower()
    if lowered in {"response time", "time"}:
        return "latency"
    return lowered or "metric"


class LibraryCompiler:
    def __init__(self, knowledge_compiler: KnowledgeCompiler | None = None) -> None:
        self.knowledge_compiler = knowledge_compiler or KnowledgeCompiler()

    def compile_workspace(self, payload: dict[str, Any]) -> CompiledBundlePayload:
        compiled_knowledge = self.knowledge_compiler.compile(payload)
        module_cards: list[ModuleCardPlus] = []
        evidence_cards: list[EvidenceCard] = []
        metric_evidence: list[MetricEvidence] = []
        retrieval_units: list[RetrievalUnit] = []

        for project_pack, project_payload in zip(compiled_knowledge.projects, _project_payloads(payload)):
            project_modules = self._build_module_cards(project_pack, project_payload)
            project_evidence = _dedupe_by_key(
                self._build_manual_evidence_cards(project_pack, project_payload)
                + self._build_evidence_cards(project_pack, project_payload),
                lambda item: item.evidence_id,
            )
            project_metrics = _dedupe_by_key(
                self._build_manual_metric_evidence(project_pack, project_payload)
                + self._build_metric_evidence(project_pack, project_payload),
                lambda item: item.evidence_id,
            )
            project_units = self._build_retrieval_units(
                project_pack,
                project_payload,
                project_modules,
                project_evidence,
                project_metrics,
            )
            project_units = _dedupe_by_key(
                self._build_manual_retrieval_units(project_pack, project_payload)
                + project_units,
                lambda item: item.unit_id,
            )
            module_cards.extend(project_modules)
            evidence_cards.extend(project_evidence)
            metric_evidence.extend(project_metrics)
            retrieval_units.extend(project_units)

        return CompiledBundlePayload(
            profile_headline=compiled_knowledge.profile_card.headline,
            compiled_knowledge=compiled_knowledge,
            module_cards=module_cards,
            evidence_cards=evidence_cards,
            metric_evidence=metric_evidence,
            retrieval_units=retrieval_units,
            terminology=list(compiled_knowledge.terminology),
        )

    def _build_module_cards(
        self,
        project_pack: ProjectInterviewPack,
        project_payload: dict[str, Any],
    ) -> list[ModuleCardPlus]:
        failure_surface = _dedupe(
            [_clean_text(item) for item in project_payload.get("failure_cases", [])]
            + [_clean_text(item) for item in project_payload.get("limitations", [])]
        )[:4]
        repo_summaries = [
            item for item in project_payload.get("repo_summaries", []) if isinstance(item, dict)
        ]
        repo_id = None
        if repo_summaries:
            repo_id = _clean_text(repo_summaries[0].get("repo_id")) or None

        module_cards: list[ModuleCardPlus] = []
        for index, module in enumerate(project_pack.key_modules):
            key_files = sorted(
                {
                    chunk.path
                    for chunk in project_pack.code_chunks
                    if chunk.module_id == module.module_id
                }
            )
            upstream = [project_pack.key_modules[index - 1].module_id] if index > 0 else []
            downstream = (
                [project_pack.key_modules[index + 1].module_id]
                if index + 1 < len(project_pack.key_modules)
                else []
            )
            key_call_paths = key_files[:3] or module.interfaces[:3]
            module_cards.append(
                ModuleCardPlus(
                    module_id=module.module_id,
                    project_id=project_pack.project_id,
                    repo_id=repo_id,
                    name=module.name,
                    responsibility=module.responsibility,
                    interfaces=list(module.interfaces),
                    dependencies=list(module.dependencies),
                    design_rationale=module.design_rationale,
                    upstream_modules=upstream,
                    downstream_modules=downstream,
                    key_call_paths=key_call_paths,
                    failure_surface=failure_surface,
                    risky_interfaces=list(module.interfaces[:3]),
                    key_files=key_files[:6],
                )
            )
        return module_cards

    def _build_manual_evidence_cards(
        self,
        project_pack: ProjectInterviewPack,
        project_payload: dict[str, Any],
    ) -> list[EvidenceCard]:
        evidence_cards: list[EvidenceCard] = []
        for index, item in enumerate(project_payload.get("manual_evidence", []), start=1):
            if not isinstance(item, dict):
                continue
            title = _clean_text(item.get("title"))
            summary = _clean_text(item.get("summary"))
            if not title and not summary:
                continue
            evidence_cards.append(
                EvidenceCard(
                    evidence_id=_clean_text(item.get("evidence_id")) or f"{project_pack.project_id}-manual-evidence-{index}",
                    project_id=project_pack.project_id,
                    module_id=_clean_text(item.get("module_id")) or None,
                    evidence_type=_clean_text(item.get("evidence_type")) or "manual_note",
                    title=title or f"Evidence {index}",
                    summary=summary,
                    source_kind=_clean_text(item.get("source_kind")) or "manual_note",
                    source_ref=_clean_text(item.get("source_ref")) or "workspace note",
                    confidence=_clean_text(item.get("confidence")) or "medium",
                )
            )
        return evidence_cards

    def _build_evidence_cards(
        self,
        project_pack: ProjectInterviewPack,
        project_payload: dict[str, Any],
    ) -> list[EvidenceCard]:
        evidence_cards: list[EvidenceCard] = []
        source_documents = [
            item for item in project_payload.get("documents", []) if isinstance(item, dict)
        ]
        for index, chunk in enumerate(project_pack.doc_chunks, start=1):
            source_document = source_documents[min(index - 1, len(source_documents) - 1)] if source_documents else {}
            source_ref = _clean_text(source_document.get("path")) or chunk.title
            evidence_cards.append(
                EvidenceCard(
                    evidence_id=f"{project_pack.project_id}-doc-evidence-{index}",
                    project_id=project_pack.project_id,
                    module_id=None,
                    evidence_type="document",
                    title=source_ref,
                    summary=chunk.summary,
                    source_kind="document",
                    source_ref=source_ref,
                    confidence="medium",
                )
            )

        if evidence_cards:
            return evidence_cards

        for index, chunk in enumerate(project_pack.code_chunks[:3], start=1):
            evidence_cards.append(
                EvidenceCard(
                    evidence_id=f"{project_pack.project_id}-code-evidence-{index}",
                    project_id=project_pack.project_id,
                    module_id=chunk.module_id,
                    evidence_type="code",
                    title=chunk.path,
                    summary=chunk.summary,
                    source_kind="code",
                    source_ref=chunk.path,
                    confidence="medium",
                )
                )
        return evidence_cards

    def _build_manual_metric_evidence(
        self,
        project_pack: ProjectInterviewPack,
        project_payload: dict[str, Any],
    ) -> list[MetricEvidence]:
        metric_evidence: list[MetricEvidence] = []
        for index, item in enumerate(project_payload.get("manual_metrics", []), start=1):
            if not isinstance(item, dict):
                continue
            metric_name = _clean_text(item.get("metric_name"))
            metric_value = _clean_text(item.get("metric_value"))
            if not metric_name and not metric_value:
                continue
            metric_evidence.append(
                MetricEvidence(
                    evidence_id=_clean_text(item.get("evidence_id")) or f"{project_pack.project_id}-manual-metric-{index}",
                    project_id=project_pack.project_id,
                    module_id=_clean_text(item.get("module_id")) or None,
                    metric_name=metric_name or "metric",
                    metric_value=metric_value,
                    baseline=_clean_text(item.get("baseline")),
                    method=_clean_text(item.get("method")) or "manual note",
                    environment=_clean_text(item.get("environment")) or "workspace",
                    source_note=_clean_text(item.get("source_note")) or "manual metric",
                    confidence=_clean_text(item.get("confidence")) or "medium",
                )
            )
        return metric_evidence

    def _build_metric_evidence(
        self,
        project_pack: ProjectInterviewPack,
        project_payload: dict[str, Any],
    ) -> list[MetricEvidence]:
        metric_evidence: list[MetricEvidence] = []
        source_documents = [
            item for item in project_payload.get("documents", []) if isinstance(item, dict)
        ]
        for document in source_documents:
            document_path = _clean_text(document.get("path")) or "document"
            text = _clean_text(document.get("content"))
            for index, match in enumerate(_METRIC_FROM_TO_PATTERN.finditer(text), start=1):
                metric_name = _normalize_metric_name(match.group("name"))
                metric_evidence.append(
                    MetricEvidence(
                        evidence_id=f"{project_pack.project_id}-metric-{len(metric_evidence) + 1}",
                        project_id=project_pack.project_id,
                        module_id=None,
                        metric_name=metric_name,
                        metric_value=_clean_text(match.group("value")),
                        baseline=_clean_text(match.group("baseline")),
                        method="document-derived note",
                        environment="workspace documents",
                        source_note=f"{document_path} match {index}",
                        confidence="medium",
                    )
                )
        return metric_evidence

    def _build_retrieval_units(
        self,
        project_pack: ProjectInterviewPack,
        project_payload: dict[str, Any],
        module_cards: list[ModuleCardPlus],
        evidence_cards: list[EvidenceCard],
        metric_evidence: list[MetricEvidence],
    ) -> list[RetrievalUnit]:
        supporting_refs = [item.evidence_id for item in evidence_cards[:3]]
        metric_refs = [item.evidence_id for item in metric_evidence[:2]]
        hooks = _dedupe(
            [_clean_text(item) for item in project_payload.get("interviewer_hooks", [])]
            + [_clean_text(item) for item in project_pack.follow_up_tree]
        )[:3]
        tradeoffs = _dedupe([_clean_text(item) for item in project_pack.tradeoffs])
        units: list[RetrievalUnit] = [
            RetrievalUnit(
                unit_id=f"{project_pack.project_id}-project-intro",
                unit_type="project_intro",
                project_id=project_pack.project_id,
                module_id=None,
                question_forms=[
                    "What does this project do?",
                    "Can you introduce this project?",
                    "Tell me about the project.",
                ],
                short_answer=project_pack.pitch_30,
                long_answer=project_pack.pitch_90,
                key_points=_dedupe(
                    [
                        project_pack.business_value,
                        project_pack.architecture,
                        tradeoffs[0] if tradeoffs else "",
                    ]
                )[:4],
                supporting_refs=supporting_refs + metric_refs[:1],
                hooks=hooks,
                safe_claims=_dedupe([project_pack.business_value, project_pack.architecture]),
            ),
            RetrievalUnit(
                unit_id=f"{project_pack.project_id}-architecture-overview",
                unit_type="architecture_overview",
                project_id=project_pack.project_id,
                module_id=None,
                question_forms=[
                    "How is the system designed?",
                    "What is the architecture?",
                    "How did you structure the project?",
                ],
                short_answer=project_pack.architecture,
                long_answer=self._build_architecture_answer(project_pack, module_cards),
                key_points=_dedupe(
                    [project_pack.architecture]
                    + [module.name for module in module_cards[:3]]
                )[:5],
                supporting_refs=supporting_refs,
                hooks=hooks,
                safe_claims=[project_pack.architecture],
            ),
        ]

        if tradeoffs:
            units.append(
                RetrievalUnit(
                    unit_id=f"{project_pack.project_id}-tradeoff-reasoning",
                    unit_type="tradeoff_reasoning",
                    project_id=project_pack.project_id,
                    module_id=None,
                    question_forms=[
                        "Why did you choose this design?",
                        "What tradeoffs did you make?",
                        "Why not use a bigger all-in-one solution?",
                    ],
                    short_answer=tradeoffs[0],
                    long_answer=" ".join(tradeoffs[:3] + project_pack.limitations[:1]).strip(),
                    key_points=tradeoffs[:4],
                    supporting_refs=supporting_refs + metric_refs[:1],
                    hooks=hooks,
                    safe_claims=tradeoffs[:3],
                )
            )

        if metric_evidence:
            first_metric = metric_evidence[0]
            units.append(
                RetrievalUnit(
                    unit_id=f"{project_pack.project_id}-performance-evidence",
                    unit_type="performance_evidence",
                    project_id=project_pack.project_id,
                    module_id=None,
                    question_forms=[
                        "Do you have any performance numbers?",
                        "How did you measure the result?",
                        "What evidence supports the improvement?",
                    ],
                    short_answer=(
                        f"{first_metric.metric_name} improved from "
                        f"{first_metric.baseline} to {first_metric.metric_value}."
                    ),
                    long_answer=(
                        f"We tracked {first_metric.metric_name} and saw it move from "
                        f"{first_metric.baseline} to {first_metric.metric_value}. "
                        f"The note came from {first_metric.source_note}."
                    ),
                    key_points=[
                        first_metric.metric_name,
                        first_metric.baseline,
                        first_metric.metric_value,
                    ],
                    supporting_refs=metric_refs + supporting_refs[:1],
                    hooks=hooks,
                    safe_claims=[
                        f"{first_metric.metric_name} improved to {first_metric.metric_value}",
                    ],
                )
            )

        for module in module_cards[:3]:
            units.append(
                RetrievalUnit(
                    unit_id=f"{project_pack.project_id}-{_slugify(module.name)}-module-deep-dive",
                    unit_type="module_deep_dive",
                    project_id=project_pack.project_id,
                    module_id=module.module_id,
                    question_forms=[
                        f"What does {module.name} do?",
                        f"How does {module.name} fit into the system?",
                        f"Can you deep dive into {module.name}?",
                    ],
                    short_answer=module.responsibility,
                    long_answer=self._build_module_answer(module, project_pack.code_chunks),
                    key_points=_dedupe(
                        [module.responsibility]
                        + module.key_call_paths
                        + module.failure_surface[:1]
                    )[:5],
                    supporting_refs=supporting_refs[:2],
                    hooks=hooks,
                    safe_claims=_dedupe([module.responsibility] + module.key_call_paths[:2]),
                )
            )
        return units

    def _build_manual_retrieval_units(
        self,
        project_pack: ProjectInterviewPack,
        project_payload: dict[str, Any],
    ) -> list[RetrievalUnit]:
        units: list[RetrievalUnit] = []
        for index, item in enumerate(project_payload.get("manual_retrieval_units", []), start=1):
            if not isinstance(item, dict):
                continue
            short_answer = _clean_text(item.get("short_answer"))
            long_answer = _clean_text(item.get("long_answer"))
            if not short_answer and not long_answer:
                continue
            units.append(
                RetrievalUnit(
                    unit_id=_clean_text(item.get("unit_id")) or f"{project_pack.project_id}-manual-ru-{index}",
                    unit_type=_clean_text(item.get("unit_type")) or "project_intro",
                    project_id=project_pack.project_id,
                    module_id=_clean_text(item.get("module_id")) or None,
                    question_forms=_dedupe([_clean_text(value) for value in item.get("question_forms", [])]),
                    short_answer=short_answer,
                    long_answer=long_answer,
                    key_points=_dedupe([_clean_text(value) for value in item.get("key_points", [])]),
                    supporting_refs=_dedupe([_clean_text(value) for value in item.get("supporting_refs", [])]),
                    hooks=_dedupe([_clean_text(value) for value in item.get("hooks", [])]),
                    safe_claims=_dedupe([_clean_text(value) for value in item.get("safe_claims", [])]),
                )
            )
        return units

    def _build_architecture_answer(
        self,
        project_pack: ProjectInterviewPack,
        module_cards: list[ModuleCardPlus],
    ) -> str:
        module_summary = ", ".join(module.name for module in module_cards[:4])
        if module_summary:
            return (
                f"{project_pack.architecture} "
                f"The core modules are {module_summary}, and each module keeps a clear boundary."
            ).strip()
        return project_pack.architecture

    def _build_module_answer(
        self,
        module: ModuleCardPlus,
        code_chunks: list[CodeChunk],
    ) -> str:
        key_files = module.key_files or [
            chunk.path
            for chunk in code_chunks
            if chunk.module_id == module.module_id
        ][:3]
        file_summary = ", ".join(PurePosixPath(path).name for path in key_files[:3])
        answer = module.responsibility
        if file_summary:
            answer = f"{answer} The main implementation lives in {file_summary}."
        if module.failure_surface:
            answer = f"{answer} The main risk area is {module.failure_surface[0]}."
        return answer.strip()
