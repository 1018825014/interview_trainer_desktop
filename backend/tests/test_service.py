import time
import unittest

from interview_trainer.generation import DualDraftComposer
from interview_trainer.service import InterviewTrainerService
from interview_trainer.types import AnswerDraft


class _DelayedProvider:
    def __init__(self, *, delay_s: float, level: str) -> None:
        self.delay_s = delay_s
        self.level = level

    def starter(self, **kwargs) -> AnswerDraft:
        return self._build(kwargs["turn_id"])

    def full(self, **kwargs) -> AnswerDraft:
        return self._build(kwargs["turn_id"])

    def _build(self, turn_id: str) -> AnswerDraft:
        time.sleep(self.delay_s)
        return AnswerDraft(
            level=self.level,
            turn_id=turn_id,
            text=f"{self.level} answer",
            bullets=[f"{self.level} bullet"],
            evidence_refs=["profile"],
        )


class _StarterOkFullFailProvider:
    def starter(self, **kwargs) -> AnswerDraft:
        return AnswerDraft(
            level="starter",
            turn_id=kwargs["turn_id"],
            text="starter answer",
            bullets=["starter bullet"],
            evidence_refs=["profile"],
        )

    def full(self, **kwargs) -> AnswerDraft:
        raise TimeoutError("full model timed out")


class _StreamingStarterProvider:
    def __init__(self, *, starter_delay_s: float = 0.35, full_delay_s: float = 0.5) -> None:
        self.starter_delay_s = starter_delay_s
        self.full_delay_s = full_delay_s

    def starter(self, **kwargs) -> AnswerDraft:
        stream_state = kwargs.get("stream_state")
        if stream_state is not None:
            stream_state.ingest('{"text":"这是一个流式起手句', parsed_text="这是一个流式起手句")
        time.sleep(self.starter_delay_s)
        return AnswerDraft(
            level="starter",
            turn_id=kwargs["turn_id"],
            text="这是一个流式起手句，先帮候选人开口。",
            bullets=["先给结论"],
            evidence_refs=["profile"],
        )

    def full(self, **kwargs) -> AnswerDraft:
        time.sleep(self.full_delay_s)
        return AnswerDraft(
            level="full",
            turn_id=kwargs["turn_id"],
            text="这是一个完整回答。",
            bullets=["业务目标", "设计取舍"],
            evidence_refs=["profile"],
        )


class InterviewTrainerServiceTests(unittest.TestCase):
    def test_answer_payload_includes_answer_plan_and_state(self) -> None:
        service = InterviewTrainerService(
            composer=DualDraftComposer(
                fast_provider=_DelayedProvider(delay_s=0.05, level="starter"),
                smart_provider=_DelayedProvider(delay_s=0.2, level="full"),
            )
        )
        session = service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/orchestrator/workflow.py", "content": "def run(): pass"}],
                        }
                    ]
                },
                "briefing": {"company": "Test", "business_context": "Agent", "job_description": "agent latency evaluation"},
            }
        )
        session_id = session["session_id"]
        service.handle_transcript(
            session_id,
            {
                "speaker": "interviewer",
                "text": "Introduce one agent project and the key tradeoffs.",
                "final": True,
                "confidence": 0.98,
                "ts_start": 0.0,
                "ts_end": 1.5,
            },
        )

        response = service.tick_session(session_id, 2.6)
        answer = response["answer"]

        self.assertEqual(answer["answer_plan"]["intent"], "tradeoff_reasoning")
        self.assertTrue(answer["answer_plan"]["allow_hook"])
        self.assertEqual(answer["answer_state"]["active_project_id"], "agentops-console")
        self.assertEqual(answer["answer_state"]["followup_thread"], "tradeoff_reasoning")

    def test_answer_generation_transitions_from_pending_to_complete(self) -> None:
        service = InterviewTrainerService(
            composer=DualDraftComposer(
                fast_provider=_DelayedProvider(delay_s=0.05, level="starter"),
                smart_provider=_DelayedProvider(delay_s=0.2, level="full"),
            )
        )
        session = service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "做 Agent 编排和 tracing。"}],
                            "code_files": [{"path": "src/orchestrator/workflow.py", "content": "def run(): pass"}],
                        }
                    ]
                },
                "briefing": {"company": "Test", "business_context": "Agent", "job_description": "agent latency evaluation"},
            }
        )
        session_id = session["session_id"]
        service.handle_transcript(
            session_id,
            {
                "speaker": "interviewer",
                "text": "介绍一下 AgentOps Console 的架构。",
                "final": True,
                "confidence": 0.98,
                "ts_start": 0.0,
                "ts_end": 1.5,
            },
        )
        response = service.tick_session(session_id, 2.6)
        self.assertIn(response["answer"]["status"], {"pending", "starter_ready"})

        time.sleep(0.08)
        starter_state = service.get_answer(session_id, response["answer"]["turn_id"])
        self.assertIn(starter_state["status"], {"starter_ready", "complete"})
        self.assertIn("starter", starter_state["drafts"])

        time.sleep(0.18)
        final_state = service.get_answer(session_id, response["answer"]["turn_id"])
        self.assertEqual(final_state["status"], "complete")
        self.assertIn("full", final_state["drafts"])

    def test_full_failure_keeps_starter_available(self) -> None:
        service = InterviewTrainerService(
            composer=DualDraftComposer(
                fast_provider=_StarterOkFullFailProvider(),
                smart_provider=_StarterOkFullFailProvider(),
            )
        )
        session = service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/orchestrator/workflow.py", "content": "def run(): pass"}],
                        }
                    ]
                },
                "briefing": {"company": "Test", "business_context": "Agent", "job_description": "agent latency evaluation"},
            }
        )
        session_id = session["session_id"]
        service.handle_transcript(
            session_id,
            {
                "speaker": "interviewer",
                "text": "Introduce one agent project and the key tradeoffs.",
                "final": True,
                "confidence": 0.98,
                "ts_start": 0.0,
                "ts_end": 1.5,
            },
        )
        response = service.tick_session(session_id, 2.6)
        final_state = service.get_answer(session_id, response["answer"]["turn_id"])
        for _ in range(10):
            if final_state["error"]:
                break
            time.sleep(0.02)
            final_state = service.get_answer(session_id, response["answer"]["turn_id"])
        self.assertEqual(final_state["status"], "starter_ready")
        self.assertIn("starter", final_state["drafts"])
        self.assertNotIn("full", final_state["drafts"])
        self.assertIn("full failed", final_state["error"])

    def test_streaming_starter_becomes_visible_before_completion(self) -> None:
        provider = _StreamingStarterProvider()
        service = InterviewTrainerService(
            composer=DualDraftComposer(
                fast_provider=provider,
                smart_provider=provider,
            )
        )
        session = service.create_session(
            {
                "knowledge": {
                    "projects": [
                        {
                            "name": "AgentOps Console",
                            "documents": [{"content": "Agent workflow builder with tracing and evaluation."}],
                            "code_files": [{"path": "src/orchestrator/workflow.py", "content": "def run(): pass"}],
                        }
                    ]
                },
                "briefing": {"company": "Test", "business_context": "Agent", "job_description": "agent latency evaluation"},
            }
        )
        session_id = session["session_id"]
        service.handle_transcript(
            session_id,
            {
                "speaker": "interviewer",
                "text": "Introduce one agent project and the key tradeoffs.",
                "final": True,
                "confidence": 0.98,
                "ts_start": 0.0,
                "ts_end": 1.5,
            },
        )
        response = service.tick_session(session_id, 2.6)
        turn_id = response["answer"]["turn_id"]

        seen = response["answer"]
        for _ in range(8):
            if seen["status"] == "starter_streaming":
                break
            time.sleep(0.02)
            seen = service.get_answer(session_id, turn_id)

        self.assertEqual(seen["status"], "starter_streaming")
        self.assertIn("starter", seen["drafts"])
        self.assertTrue(seen["drafts"]["starter"].get("streaming"))
        self.assertIsNotNone(seen["metrics"]["starter_stream_ms"])
        self.assertIn("流式起手句", seen["drafts"]["starter"]["text"])


if __name__ == "__main__":
    unittest.main()
