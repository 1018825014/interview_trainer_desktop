import unittest

from interview_trainer.turns import TurnManager
from interview_trainer.types import Speaker, TranscriptEvent, TurnMode


class TurnManagerTests(unittest.TestCase):
    def test_locks_question_after_silence(self) -> None:
        manager = TurnManager(silence_lock_s=0.5)
        manager.ingest(
            TranscriptEvent(
                speaker=Speaker.INTERVIEWER,
                text="介绍一下你做过的 Agent 项目",
                final=True,
                confidence=0.98,
                ts_start=0.0,
                ts_end=2.0,
            )
        )

        decision = manager.tick(2.7)
        self.assertTrue(decision.should_generate)
        self.assertEqual(decision.mode, TurnMode.LOCKED_QUESTION)
        self.assertIn("Agent 项目", decision.locked_question)

    def test_candidate_immediate_response_still_locks_question(self) -> None:
        manager = TurnManager()
        manager.ingest(
            TranscriptEvent(
                speaker=Speaker.INTERVIEWER,
                text="为什么你没有直接做 multi-agent？",
                final=True,
                confidence=0.96,
                ts_start=0.0,
                ts_end=2.8,
            )
        )
        decision = manager.ingest(
            TranscriptEvent(
                speaker=Speaker.CANDIDATE,
                text="我当时优先考虑稳定性。",
                final=False,
                confidence=0.91,
                ts_start=2.9,
                ts_end=3.4,
            )
        )
        self.assertTrue(decision.should_generate)
        self.assertEqual(decision.mode, TurnMode.CANDIDATE_ANSWERING)
        self.assertIn("multi-agent", decision.locked_question)

    def test_overlap_state_when_candidate_interrupts_before_question_complete(self) -> None:
        manager = TurnManager()
        manager.ingest(
            TranscriptEvent(
                speaker=Speaker.INTERVIEWER,
                text="你们项目里的检索是怎么设计的？",
                final=False,
                confidence=0.94,
                ts_start=0.0,
                ts_end=3.0,
            )
        )
        decision = manager.ingest(
            TranscriptEvent(
                speaker=Speaker.CANDIDATE,
                text="我可以先讲整体架构。",
                final=False,
                confidence=0.88,
                ts_start=3.1,
                ts_end=3.5,
            )
        )
        self.assertEqual(decision.mode, TurnMode.OVERLAP)
        self.assertFalse(decision.should_generate)


if __name__ == "__main__":
    unittest.main()
