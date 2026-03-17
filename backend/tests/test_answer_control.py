from __future__ import annotations

import unittest

from interview_trainer.answer_control import AnswerController, AnswerState


class AnswerControlTests(unittest.TestCase):
    def test_tradeoff_question_builds_tradeoff_answer_plan(self) -> None:
        controller = AnswerController()

        plan = controller.build_plan(
            question="为什么这个项目这样设计，而不是做成一个一体化工作流？",
            route_mode="project",
            active_project_ids=["agent-console"],
        )

        self.assertEqual(plan.intent, "tradeoff_reasoning")
        self.assertTrue(plan.allow_hook)
        self.assertIn("RetrievalUnit", plan.retrieve_priority)
        self.assertFalse(plan.need_code_evidence)

    def test_followup_reuses_previous_project_state(self) -> None:
        controller = AnswerController()
        previous = AnswerState(active_project_id="agent-console", followup_thread="architecture_overview")

        plan = controller.build_plan(
            question="这个模块为什么会成为瓶颈？",
            route_mode="project",
            active_project_ids=[],
            previous_state=previous,
        )
        next_state = controller.advance_state(
            previous_state=previous,
            plan=plan,
            active_project_ids=[],
            active_module_ids=["retrieval-router"],
            question="这个模块为什么会成为瓶颈？",
        )

        self.assertEqual(plan.intent, "module_deep_dive")
        self.assertEqual(next_state.active_project_id, "agent-console")
        self.assertEqual(next_state.active_module_id, "retrieval-router")
        self.assertEqual(next_state.followup_thread, "module_deep_dive")


if __name__ == "__main__":
    unittest.main()
