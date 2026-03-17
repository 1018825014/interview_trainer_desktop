from __future__ import annotations

from dataclasses import dataclass, field

from .types import Speaker, TranscriptEvent, TurnDecision, TurnMode


@dataclass(slots=True)
class TurnManager:
    overlap_window_s: float = 0.75
    silence_lock_s: float = 0.9
    _mode: TurnMode = field(default=TurnMode.LISTENING, init=False)
    _interviewer_buffer: list[str] = field(default_factory=list, init=False)
    _candidate_buffer: list[str] = field(default_factory=list, init=False)
    _last_interviewer_end: float = field(default=0.0, init=False)
    _last_candidate_end: float = field(default=0.0, init=False)
    _question_locked: bool = field(default=False, init=False)
    _interviewer_final_received: bool = field(default=False, init=False)
    _current_turn_id: str = field(default="", init=False)
    _turn_counter: int = field(default=0, init=False)

    def ingest(self, event: TranscriptEvent) -> TurnDecision:
        if event.speaker == Speaker.INTERVIEWER:
            return self._ingest_interviewer(event)
        return self._ingest_candidate(event)

    def tick(self, now_ts: float) -> TurnDecision:
        if (
            self._interviewer_buffer
            and self._interviewer_final_received
            and not self._question_locked
            and now_ts - self._last_interviewer_end >= self.silence_lock_s
        ):
            self._question_locked = True
            self._mode = TurnMode.LOCKED_QUESTION
            return TurnDecision(
                mode=self._mode,
                turn_id=self._current_turn_id,
                should_generate=True,
                locked_question=self.current_question(),
            )
        return TurnDecision(mode=self._mode, turn_id=self._current_turn_id)

    def current_question(self) -> str:
        return " ".join(chunk for chunk in self._interviewer_buffer if chunk).strip()

    def current_candidate_answer(self) -> str:
        return " ".join(chunk for chunk in self._candidate_buffer if chunk).strip()

    def _start_new_turn(self) -> None:
        self._turn_counter += 1
        self._current_turn_id = f"turn-{self._turn_counter}"
        self._interviewer_buffer.clear()
        self._candidate_buffer.clear()
        self._question_locked = False
        self._interviewer_final_received = False

    def _ingest_interviewer(self, event: TranscriptEvent) -> TurnDecision:
        if not self._current_turn_id or (
            self._mode == TurnMode.CANDIDATE_ANSWERING
            and event.ts_start - self._last_candidate_end > self.overlap_window_s
        ):
            self._start_new_turn()

        overlap = self._last_candidate_end and event.ts_start <= self._last_candidate_end + self.overlap_window_s
        self._mode = TurnMode.OVERLAP if overlap else TurnMode.LISTENING
        self._interviewer_buffer.append(event.text.strip())
        self._last_interviewer_end = event.ts_end
        self._interviewer_final_received = event.final or self._interviewer_final_received
        return TurnDecision(
            mode=self._mode,
            turn_id=self._current_turn_id,
            overlap_detected=bool(overlap),
        )

    def _ingest_candidate(self, event: TranscriptEvent) -> TurnDecision:
        if not self._current_turn_id and event.text.strip():
            self._start_new_turn()

        should_generate = False
        locked_question = ""
        if self._interviewer_buffer and self._interviewer_final_received and not self._question_locked:
            self._question_locked = True
            should_generate = True
            locked_question = self.current_question()

        overlap = (
            self._interviewer_buffer
            and not self._question_locked
            and event.ts_start <= self._last_interviewer_end + self.overlap_window_s
        )
        self._mode = TurnMode.OVERLAP if overlap else TurnMode.CANDIDATE_ANSWERING
        self._candidate_buffer.append(event.text.strip())
        self._last_candidate_end = event.ts_end
        return TurnDecision(
            mode=self._mode,
            turn_id=self._current_turn_id,
            should_generate=should_generate,
            locked_question=locked_question,
            overlap_detected=bool(overlap),
        )
