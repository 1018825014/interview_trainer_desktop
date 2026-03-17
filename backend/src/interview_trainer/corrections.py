from __future__ import annotations

import difflib
from typing import Iterable

from .types import CorrectionSuggestion, TranscriptEvent


class TerminologyCorrector:
    """Surface only high-value quick-fix suggestions for low-confidence transcripts."""

    def __init__(self, glossary: Iterable[str]) -> None:
        self.glossary = [term for term in glossary if term]

    def inspect(self, event: TranscriptEvent) -> list[CorrectionSuggestion]:
        if event.confidence >= 0.82:
            return []
        suggestions: list[CorrectionSuggestion] = []
        tokens = [
            token.strip("()[]{}:,.'\"")
            for token in event.text.replace("/", " ").replace("-", " ").split()
            if len(token.strip("()[]{}:,.'\"")) >= 3
        ]
        for token in tokens[:8]:
            matches = difflib.get_close_matches(token, self.glossary, n=3, cutoff=0.75)
            if matches and token not in matches:
                suggestions.append(
                    CorrectionSuggestion(
                        source_term=token,
                        replacements=matches,
                        reason="这是低置信度术语，建议一键替换，而不是手动重写整句话。",
                    )
                )
        return suggestions
