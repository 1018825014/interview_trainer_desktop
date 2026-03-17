from __future__ import annotations

import threading
from dataclasses import asdict, replace
from uuid import uuid4

from .answer_control import AnswerController, AnswerState
from .briefing import BriefingBuilder
from .config import GenerationSettings, list_fast_model_presets
from .config import _resolve_fast_model_preset
from .corrections import TerminologyCorrector
from .generation import DraftFutures, DualDraftComposer, StarterPrewarm, build_dual_draft_composer
from .knowledge import KnowledgeCompiler
from .library_compile import LibraryCompiler
from .routing import ContextRouter
from .turns import TurnManager
from .types import (
    AnswerStatus,
    CompiledKnowledge,
    InterviewSession,
    SessionBriefing,
    Speaker,
    TranscriptEvent,
    TurnDecision,
)


class InterviewTrainerService:
    _PREWARM_MIN_CHARS = 32

    def __init__(
        self,
        *,
        knowledge_compiler: KnowledgeCompiler | None = None,
        router: ContextRouter | None = None,
        answer_controller: AnswerController | None = None,
        briefing_builder: BriefingBuilder | None = None,
        composer: DualDraftComposer | None = None,
        settings: GenerationSettings | None = None,
    ) -> None:
        self.settings = settings or GenerationSettings.from_env()
        self.knowledge_compiler = knowledge_compiler or KnowledgeCompiler()
        self.library_compiler = LibraryCompiler(self.knowledge_compiler)
        self.router = router or ContextRouter()
        self.answer_controller = answer_controller or AnswerController()
        self.briefing_builder = briefing_builder or BriefingBuilder()
        self.composer = composer or build_dual_draft_composer(self.settings)
        self.sessions: dict[str, InterviewSession] = {}
        self.turn_managers: dict[str, TurnManager] = {}
        self.pending_answer_jobs: dict[str, dict[str, DraftFutures]] = {}
        self.answer_states: dict[str, AnswerState] = {}
        self.pending_prewarm_jobs: dict[str, dict[str, StarterPrewarm]] = {}
        self._lock = threading.RLock()

    def compile_knowledge(self, payload: dict) -> dict:
        with self._lock:
            knowledge = self.knowledge_compiler.compile(payload)
            return self.knowledge_compiler.to_dict(knowledge)

    def create_session(self, payload: dict) -> dict:
        with self._lock:
            knowledge_payload = payload.get("knowledge", {})
            bundle = None
            if isinstance(knowledge_payload, CompiledKnowledge):
                knowledge = knowledge_payload
            else:
                bundle = self.library_compiler.compile_workspace(knowledge_payload)
                knowledge = bundle.compiled_knowledge
            briefing = self._build_briefing(payload.get("briefing", {}), knowledge)
            session_id = payload.get("session_id") or str(uuid4())
            self.sessions[session_id] = InterviewSession(
                session_id=session_id,
                knowledge=knowledge,
                briefing=briefing,
                library_bundle=bundle,
            )
            self.turn_managers[session_id] = TurnManager()
            self.pending_answer_jobs[session_id] = {}
            self.answer_states[session_id] = AnswerState()
            self.pending_prewarm_jobs[session_id] = {}
            return {
                "session_id": session_id,
                "briefing": asdict(briefing),
                "generation": self.get_generation_settings(),
                "knowledge_overview": {
                    "projects": [project.name for project in knowledge.projects],
                    "role_playbooks": [playbook.role_name for playbook in knowledge.role_playbooks],
                },
            }

    def get_generation_settings(self) -> dict:
        with self._lock:
            return self._serialize_generation_settings()

    def update_generation_settings(self, payload: dict) -> dict:
        with self._lock:
            next_settings = self.settings

            if "fast_preset" in payload:
                preset = _resolve_fast_model_preset(str(payload.get("fast_preset", "")))
                if preset is None:
                    raise ValueError("fast_preset cannot be empty")
                next_settings = replace(
                    next_settings,
                    fast_model=preset.model,
                    fast_preset=preset.name,
                    fast_enable_thinking=preset.enable_thinking,
                )

            if "fast_enable_thinking" in payload:
                value = payload["fast_enable_thinking"]
                if value is None or isinstance(value, bool):
                    fast_enable_thinking = value
                else:
                    raise ValueError("fast_enable_thinking must be a boolean or null")
                next_settings = replace(next_settings, fast_enable_thinking=fast_enable_thinking)

            if next_settings is self.settings:
                return self._serialize_generation_settings()

            old_composer = self.composer
            self.settings = next_settings
            self.composer = build_dual_draft_composer(self.settings)
            if hasattr(old_composer, "shutdown"):
                old_composer.shutdown(wait=False)
            return self._serialize_generation_settings()

    def handle_transcript(self, session_id: str, payload: dict) -> dict:
        with self._lock:
            session = self.sessions[session_id]
            turn_manager = self.turn_managers[session_id]
            event = TranscriptEvent(
                speaker=payload["speaker"] if isinstance(payload["speaker"], Speaker) else Speaker(payload["speaker"]),
                text=payload["text"],
                final=payload["final"],
                confidence=payload["confidence"],
                ts_start=payload["ts_start"],
                ts_end=payload["ts_end"],
                turn_id=payload.get("turn_id", ""),
            )
            session.transcript_history.append(event)

            if event.speaker.value == "candidate" and event.final and event.text.strip():
                session.actual_candidate_history.append(event.text.strip())

            decision = turn_manager.ingest(event)
            self._prune_stale_prewarms(session_id, keep_turn_id=decision.turn_id)
            self._maybe_start_prewarm(session_id, session, turn_manager, event, decision)
            if not decision.should_generate:
                timer_decision = turn_manager.tick(event.ts_end)
                if timer_decision.should_generate:
                    decision = timer_decision

            response = {
                "turn": {
                    "mode": decision.mode.value,
                    "turn_id": decision.turn_id,
                    "overlap_detected": decision.overlap_detected,
                },
                "corrections": [
                    asdict(item)
                    for item in TerminologyCorrector(session.knowledge.terminology).inspect(event)
                ],
                "prewarm": self._serialize_prewarm(session_id, decision.turn_id),
            }
            response.update(self._build_answer_payload(session_id, session, decision))
            return response

    def tick_session(self, session_id: str, now_ts: float) -> dict:
        with self._lock:
            session = self.sessions[session_id]
            decision = self.turn_managers[session_id].tick(now_ts)
            response = {
                "turn": {
                    "mode": decision.mode.value,
                    "turn_id": decision.turn_id,
                    "overlap_detected": decision.overlap_detected,
                },
                "corrections": [],
                "prewarm": self._serialize_prewarm(session_id, decision.turn_id),
            }
            response.update(self._build_answer_payload(session_id, session, decision))
            return response

    def get_session(self, session_id: str) -> dict:
        with self._lock:
            session = self.sessions[session_id]
            self._collect_all_pending(session_id, session)
            return {
                "session_id": session_id,
                "briefing": asdict(session.briefing),
                "transcript_history": [asdict(item) for item in session.transcript_history],
                "actual_candidate_history": session.actual_candidate_history,
                "prewarms": [
                    payload
                    for turn_id in sorted(self.pending_prewarm_jobs.get(session_id, {}))
                    if (payload := self._serialize_prewarm(session_id, turn_id)) is not None
                ],
                "answers": session.answer_history,
            }

    def get_answer(self, session_id: str, turn_id: str) -> dict:
        with self._lock:
            session = self.sessions[session_id]
            self._collect_answer_update(session_id, session, turn_id)
            if turn_id not in session.answer_history:
                raise KeyError(turn_id)
            return session.answer_history[turn_id]

    def _build_briefing(self, payload: dict, knowledge: CompiledKnowledge) -> SessionBriefing:
        return self.briefing_builder.build(
            company=payload.get("company", ""),
            business_context=payload.get("business_context", ""),
            job_description=payload.get("job_description", ""),
            knowledge=knowledge,
        )

    def _serialize_generation_settings(self) -> dict:
        return {
            "provider": self.settings.provider,
            "base_url": self.settings.openai_base_url,
            "enable_thinking": self.settings.enable_thinking,
            "fast_provider": self.settings.fast_provider,
            "fast_base_url": self.settings.fast_base_url,
            "fast_model": self.settings.fast_model,
            "fast_preset": self.settings.fast_preset,
            "fast_enable_thinking": self.settings.fast_enable_thinking,
            "smart_provider": self.settings.smart_provider,
            "smart_base_url": self.settings.smart_base_url,
            "smart_model": self.settings.smart_model,
            "smart_enable_thinking": self.settings.smart_enable_thinking,
            "fast_preset_options": [
                {
                    "value": preset.name,
                    "model": preset.model,
                    "enable_thinking": preset.enable_thinking,
                }
                for preset in list_fast_model_presets()
            ],
        }

    def _build_answer_payload(self, session_id: str, session: InterviewSession, decision: TurnDecision) -> dict:
        if not decision.should_generate or not decision.locked_question or not decision.turn_id:
            if decision.turn_id:
                self._collect_answer_update(session_id, session, decision.turn_id)
                if decision.turn_id in session.answer_history:
                    return {"answer": session.answer_history[decision.turn_id]}
            return {}

        if decision.turn_id not in session.answer_history:
            route = self.router.route(decision.locked_question, session.knowledge, session.briefing)
            provisional_pack = self.router.build_pack(decision.locked_question, route, session.knowledge)
            previous_state = self.answer_states.get(session_id, AnswerState())
            answer_plan = self.answer_controller.build_plan(
                question=decision.locked_question,
                route_mode=route.mode.value,
                active_project_ids=[item.ref_id for item in provisional_pack.project_refs],
                active_module_ids=[item.ref_id for item in provisional_pack.module_refs],
                previous_state=previous_state,
            )
            if session.library_bundle is not None:
                pack = self.router.build_pack_for_plan(
                    question=decision.locked_question,
                    plan=answer_plan,
                    compiled_bundle=session.library_bundle,
                    route=route,
                    briefing=session.briefing,
                    answer_state=previous_state,
                )
            else:
                pack = self.router.build_pack(
                    decision.locked_question,
                    route,
                    session.knowledge,
                    answer_plan=answer_plan,
                )
            answer_state = self.answer_controller.advance_state(
                previous_state=previous_state,
                plan=answer_plan,
                active_project_ids=[item.ref_id for item in pack.project_refs],
                active_module_ids=[item.ref_id for item in pack.module_refs],
                question=decision.locked_question,
                used_hook_ids=[item.ref_id for item in pack.hook_refs],
            )
            self.answer_states[session_id] = answer_state
            prewarm = self._pop_matching_prewarm(session_id, decision.turn_id, decision.locked_question)
            session.answer_history[decision.turn_id] = {
                "turn_id": decision.turn_id,
                "question": decision.locked_question,
                "route": asdict(route),
                "answer_plan": asdict(answer_plan),
                "answer_state": asdict(answer_state),
                "pack": asdict(pack),
                "status": AnswerStatus.PENDING.value,
                "drafts": {},
                "metrics": {
                    "starter_stream_ms": None,
                    "starter_ms": None,
                    "full_ms": None,
                },
                "prewarmed_starter": bool(prewarm),
                "error": "",
            }
            if prewarm is not None:
                self.pending_answer_jobs[session_id][decision.turn_id] = self.composer.start_with_existing_starter(
                    prewarm=prewarm,
                    route=route,
                    pack=pack,
                    knowledge=session.knowledge,
                    briefing=session.briefing,
                    candidate_history=session.actual_candidate_history,
                    answer_plan=answer_plan,
                    answer_state=answer_state,
                )
            else:
                self.pending_answer_jobs[session_id][decision.turn_id] = self.composer.start(
                    turn_id=decision.turn_id,
                    question=decision.locked_question,
                    route=route,
                    pack=pack,
                    knowledge=session.knowledge,
                    briefing=session.briefing,
                    candidate_history=session.actual_candidate_history,
                    answer_plan=answer_plan,
                    answer_state=answer_state,
                )

        self._collect_answer_update(session_id, session, decision.turn_id)
        return {"answer": session.answer_history[decision.turn_id]}

    def _collect_all_pending(self, session_id: str, session: InterviewSession) -> None:
        for turn_id in list(self.pending_answer_jobs.get(session_id, {})):
            self._collect_answer_update(session_id, session, turn_id)

    def _collect_answer_update(self, session_id: str, session: InterviewSession, turn_id: str) -> None:
        pending = self.pending_answer_jobs.get(session_id, {}).get(turn_id)
        answer = session.answer_history.get(turn_id)
        if not pending or not answer:
            return

        try:
            ready = self.composer.collect_ready(pending)
        except Exception as exc:
            answer["status"] = AnswerStatus.FAILED.value
            answer["error"] = str(exc)
            self.pending_answer_jobs[session_id].pop(turn_id, None)
            return

        for level, outcome in ready.items():
            answer["drafts"][level] = asdict(outcome.draft)
            answer["metrics"][f"{level}_ms"] = round(outcome.latency_ms, 2)

        starter_snapshot = None
        if pending.starter_stream_state is not None:
            starter_snapshot = pending.starter_stream_state.snapshot()
            has_partial_starter = len(starter_snapshot.parsed_text.strip()) >= 4
            if (
                has_partial_starter
                and starter_snapshot.first_partial_at_perf is not None
                and answer["metrics"]["starter_stream_ms"] is None
            ):
                answer["metrics"]["starter_stream_ms"] = round(
                    (starter_snapshot.first_partial_at_perf - pending.started_at) * 1000,
                    2,
                )
            if (
                has_partial_starter
                and not pending.starter_future.done()
                and "starter" not in answer["drafts"]
            ):
                answer["drafts"]["starter"] = {
                    "level": "starter",
                    "turn_id": turn_id,
                    "text": starter_snapshot.parsed_text,
                    "bullets": [],
                    "evidence_refs": [],
                    "streaming": True,
                    "updated_at": starter_snapshot.updated_at,
                }
                answer["status"] = AnswerStatus.STARTER_STREAMING.value

        starter_done = pending.starter_future.done()
        full_done = pending.full_future.done()

        if (
            not starter_done
            and starter_snapshot is not None
            and len(starter_snapshot.parsed_text.strip()) >= 4
        ):
            answer["status"] = AnswerStatus.STARTER_STREAMING.value
            return

        if starter_done and not full_done:
            if pending.starter_future.exception() is None:
                answer["status"] = AnswerStatus.STARTER_READY.value
            return

        if starter_done and full_done:
            starter_error = pending.starter_future.exception()
            full_error = pending.full_future.exception()
            if starter_error and full_error:
                answer["status"] = AnswerStatus.FAILED.value
                answer["error"] = f"starter failed: {starter_error}; full failed: {full_error}"
            elif starter_error and not full_error:
                answer["status"] = AnswerStatus.COMPLETE.value
                answer["error"] = f"starter failed: {starter_error}"
            elif full_error and not starter_error:
                answer["status"] = AnswerStatus.STARTER_READY.value
                answer["error"] = f"full failed: {full_error}"
            else:
                answer["status"] = AnswerStatus.COMPLETE.value
            self.pending_answer_jobs[session_id].pop(turn_id, None)

    def _maybe_start_prewarm(
        self,
        session_id: str,
        session: InterviewSession,
        turn_manager: TurnManager,
        event: TranscriptEvent,
        decision: TurnDecision,
    ) -> None:
        if event.speaker != Speaker.INTERVIEWER or not decision.turn_id:
            return
        if decision.should_generate or decision.overlap_detected:
            return
        if decision.turn_id in session.answer_history:
            return
        if decision.turn_id in self.pending_prewarm_jobs[session_id]:
            return
        question_seed = turn_manager.current_question().strip()
        if len(question_seed) < self._PREWARM_MIN_CHARS:
            return

        route = self.router.route(question_seed, session.knowledge, session.briefing)
        pack = self.router.build_pack(question_seed, route, session.knowledge)
        self.pending_prewarm_jobs[session_id][decision.turn_id] = self.composer.start_starter_prewarm(
            turn_id=decision.turn_id,
            question=question_seed,
            route=route,
            pack=pack,
            knowledge=session.knowledge,
            briefing=session.briefing,
            candidate_history=session.actual_candidate_history,
        )

    def _prune_stale_prewarms(self, session_id: str, *, keep_turn_id: str | None) -> None:
        pending = self.pending_prewarm_jobs.get(session_id)
        if not pending:
            return
        for turn_id in list(pending):
            if keep_turn_id and turn_id == keep_turn_id:
                continue
            self._discard_prewarm(session_id, turn_id)

    def _discard_prewarm(self, session_id: str, turn_id: str) -> None:
        prewarm = self.pending_prewarm_jobs.get(session_id, {}).pop(turn_id, None)
        if prewarm is None:
            return
        if not prewarm.starter_future.done():
            prewarm.starter_future.cancel()

    def _pop_matching_prewarm(
        self,
        session_id: str,
        turn_id: str,
        locked_question: str,
    ) -> StarterPrewarm | None:
        prewarm = self.pending_prewarm_jobs.get(session_id, {}).pop(turn_id, None)
        if prewarm is None:
            return None

        seed = prewarm.question.strip()
        question = locked_question.strip()
        if not seed or not question:
            return None
        if question.startswith(seed) or seed.startswith(question) or seed in question or question in seed:
            prewarm.question = question
            return prewarm
        if not prewarm.starter_future.done():
            prewarm.starter_future.cancel()
        return None

    def _serialize_prewarm(self, session_id: str, turn_id: str | None) -> dict | None:
        if not turn_id:
            return None
        prewarm = self.pending_prewarm_jobs.get(session_id, {}).get(turn_id)
        if prewarm is None:
            return None

        status = "warming"
        text_preview = ""
        starter_stream_ms = None
        starter_ms = None
        error = ""

        snapshot = prewarm.starter_stream_state.snapshot() if prewarm.starter_stream_state is not None else None
        if snapshot is not None and snapshot.parsed_text.strip():
            text_preview = snapshot.parsed_text.strip()
            if snapshot.first_partial_at_perf is not None:
                starter_stream_ms = round((snapshot.first_partial_at_perf - prewarm.started_at) * 1000, 2)
            status = "streaming"

        if prewarm.starter_future.cancelled():
            status = "cancelled"
        elif prewarm.starter_future.done():
            exc = prewarm.starter_future.exception()
            if exc is not None:
                status = "failed"
                error = str(exc)
            else:
                outcome = prewarm.starter_future.result()
                status = "ready"
                text_preview = outcome.draft.text
                starter_ms = round(outcome.latency_ms, 2)

        return {
            "turn_id": turn_id,
            "question": prewarm.question,
            "status": status,
            "text_preview": text_preview,
            "starter_stream_ms": starter_stream_ms,
            "starter_ms": starter_ms,
            "error": error,
        }
