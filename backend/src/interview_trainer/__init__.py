"""Core package for the Windows interview trainer MVP."""

from .briefing import BriefingBuilder
from .audio import AudioProbe, AudioSessionManager
from .config import GenerationSettings, TranscriptionSettings
from .generation import DualDraftComposer, TemplateLLMProvider, build_dual_draft_composer
from .knowledge import KnowledgeCompiler
from .routing import ContextRouter
from .service import InterviewTrainerService
from .transcription import AudioTranscriptionService
from .turns import TurnManager

__all__ = [
    "AudioTranscriptionService",
    "BriefingBuilder",
    "AudioProbe",
    "AudioSessionManager",
    "ContextRouter",
    "DualDraftComposer",
    "GenerationSettings",
    "InterviewTrainerService",
    "KnowledgeCompiler",
    "TemplateLLMProvider",
    "TranscriptionSettings",
    "TurnManager",
    "build_dual_draft_composer",
]
