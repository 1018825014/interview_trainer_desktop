import unittest

from interview_trainer.knowledge import KnowledgeCompiler


class KnowledgeCompilerTests(unittest.TestCase):
    def test_builds_interview_pack_with_modules_and_terms(self) -> None:
        compiler = KnowledgeCompiler()
        knowledge = compiler.compile(
            {
                "profile": {"headline": "LLM 应用工程师"},
                "projects": [
                    {
                        "name": "Interview Brain",
                        "business_value": "做实时训练辅助。",
                        "documents": [{"content": "系统分成转写、路由、回答生成和复盘几个模块。"}],
                        "code_files": [
                            {
                                "path": "src/router/context_router.py",
                                "content": "class ContextRouter:\n    pass\n",
                            },
                            {
                                "path": "src/answer/composer.py",
                                "content": "class Composer:\n    pass\n",
                            },
                        ],
                    }
                ],
            }
        )

        self.assertEqual(knowledge.projects[0].name, "Interview Brain")
        self.assertGreaterEqual(len(knowledge.projects[0].key_modules), 1)
        self.assertGreaterEqual(len(knowledge.projects[0].code_chunks), 1)
        self.assertIn("Interview Brain", knowledge.terminology)


if __name__ == "__main__":
    unittest.main()
