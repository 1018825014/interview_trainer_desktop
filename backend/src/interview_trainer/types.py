from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AudioSource(str, Enum):
    SYSTEM = "system"
    MIC = "mic"


class Speaker(str, Enum):
    INTERVIEWER = "interviewer"
    CANDIDATE = "candidate"


class TurnMode(str, Enum):
    LISTENING = "listening"
    OVERLAP = "overlap"
    LOCKED_QUESTION = "locked_question"
    CANDIDATE_ANSWERING = "candidate_answering"


class ContextMode(str, Enum):
    GENERIC = "generic"
    PROJECT = "project"
    ROLE = "role"
    HYBRID = "hybrid"


class AnswerStatus(str, Enum):
    PENDING = "pending"
    STARTER_STREAMING = "starter_streaming"
    STARTER_READY = "starter_ready"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(slots=True)
class AudioFrame:
    source: AudioSource
    ts: float
    pcm: bytes


@dataclass(slots=True)
class TranscriptEvent:
    speaker: Speaker
    text: str
    final: bool
    confidence: float
    ts_start: float
    ts_end: float
    turn_id: str = ""


@dataclass(slots=True)
class EvidenceRef:
    ref_id: str
    label: str
    kind: str
    snippet: str


@dataclass(slots=True)
class ProfileCard:
    headline: str
    strengths: list[str]
    target_roles: list[str]
    intro_material: list[str]


@dataclass(slots=True)
class ModuleCard:
    module_id: str
    name: str
    responsibility: str
    interfaces: list[str]
    dependencies: list[str]
    design_rationale: str


@dataclass(slots=True)
class RepoMap:
    entrypoints: list[str]
    key_paths: list[str]
    module_relationships: list[str]
    summary: str


@dataclass(slots=True)
class CodebaseSummary:
    language: str
    summary: str
    repo_map: RepoMap


@dataclass(slots=True)
class DocChunk:
    chunk_id: str
    title: str
    summary: str
    text: str
    keywords: list[str]


@dataclass(slots=True)
class CodeChunk:
    chunk_id: str
    path: str
    summary: str
    code: str
    keywords: list[str]
    module_id: str


@dataclass(slots=True)
class ProjectInterviewPack:
    project_id: str
    name: str
    pitch_30: str
    pitch_90: str
    business_value: str
    architecture: str
    key_modules: list[ModuleCard]
    key_metrics: list[str]
    tradeoffs: list[str]
    failure_cases: list[str]
    limitations: list[str]
    upgrade_plan: list[str]
    follow_up_tree: list[str]
    codebase_summary: CodebaseSummary
    doc_chunks: list[DocChunk]
    code_chunks: list[CodeChunk]


@dataclass(slots=True)
class RolePlaybook:
    playbook_id: str
    role_name: str
    focus_areas: list[str]
    answer_frames: list[str]
    follow_up_patterns: list[str]


@dataclass(slots=True)
class CompiledKnowledge:
    profile_card: ProfileCard
    projects: list[ProjectInterviewPack]
    role_playbooks: list[RolePlaybook]
    terminology: list[str]


@dataclass(slots=True)
class ContextRoute:
    mode: ContextMode
    reason: str


@dataclass(slots=True)
class KnowledgePack:
    profile_refs: list[EvidenceRef] = field(default_factory=list)
    retrieval_refs: list[EvidenceRef] = field(default_factory=list)
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    project_refs: list[EvidenceRef] = field(default_factory=list)
    module_refs: list[EvidenceRef] = field(default_factory=list)
    code_refs: list[EvidenceRef] = field(default_factory=list)
    role_refs: list[EvidenceRef] = field(default_factory=list)


@dataclass(slots=True)
class AnswerDraft:
    level: str
    turn_id: str
    text: str
    bullets: list[str]
    evidence_refs: list[str]


@dataclass(slots=True)
class SessionBriefing:
    company: str
    business_context: str
    job_description: str
    priority_projects: list[str]
    focus_topics: list[str]
    style_bias: list[str]
    likely_questions: list[str]


@dataclass(slots=True)
class TurnDecision:
    mode: TurnMode
    turn_id: str | None = None
    should_generate: bool = False
    locked_question: str = ""
    overlap_detected: bool = False


@dataclass(slots=True)
class CorrectionSuggestion:
    source_term: str
    replacements: list[str]
    reason: str


@dataclass(slots=True)
class InterviewSession:
    session_id: str
    knowledge: CompiledKnowledge
    briefing: SessionBriefing
    library_bundle: Any | None = None
    transcript_history: list[TranscriptEvent] = field(default_factory=list)
    actual_candidate_history: list[str] = field(default_factory=list)
    answer_history: dict[str, dict[str, Any]] = field(default_factory=dict)
