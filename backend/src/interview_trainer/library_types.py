from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .types import CompiledKnowledge


@dataclass(slots=True)
class ModuleCardPlus:
    module_id: str
    project_id: str
    repo_id: str | None
    name: str
    responsibility: str
    interfaces: list[str]
    dependencies: list[str]
    design_rationale: str
    upstream_modules: list[str]
    downstream_modules: list[str]
    key_call_paths: list[str]
    failure_surface: list[str]
    risky_interfaces: list[str]
    key_files: list[str]


@dataclass(slots=True)
class EvidenceCard:
    evidence_id: str
    project_id: str
    module_id: str | None
    evidence_type: str
    title: str
    summary: str
    source_kind: str
    source_ref: str
    confidence: str


@dataclass(slots=True)
class MetricEvidence:
    evidence_id: str
    project_id: str
    module_id: str | None
    metric_name: str
    metric_value: str
    baseline: str
    method: str
    environment: str
    source_note: str
    confidence: str = "medium"


@dataclass(slots=True)
class RetrievalUnit:
    unit_id: str
    unit_type: str
    project_id: str
    module_id: str | None
    question_forms: list[str]
    short_answer: str
    long_answer: str
    key_points: list[str]
    supporting_refs: list[str]
    hooks: list[str]
    safe_claims: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CompiledBundlePayload:
    profile_headline: str
    compiled_knowledge: CompiledKnowledge
    module_cards: list[ModuleCardPlus]
    evidence_cards: list[EvidenceCard]
    metric_evidence: list[MetricEvidence]
    retrieval_units: list[RetrievalUnit]
    terminology: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
