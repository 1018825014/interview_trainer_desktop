from __future__ import annotations

from .types import CompiledKnowledge, SessionBriefing


class BriefingBuilder:
    def build(
        self,
        *,
        company: str,
        business_context: str,
        job_description: str,
        knowledge: CompiledKnowledge,
    ) -> SessionBriefing:
        jd = (job_description or "").lower()
        focus_topics = []
        topic_keywords = [
            "agent",
            "rag",
            "evaluation",
            "latency",
            "cost",
            "tool",
            "workflow",
            "observability",
            "prompt",
        ]
        for keyword in topic_keywords:
            if keyword in jd and keyword not in focus_topics:
                focus_topics.append(keyword)
        if not focus_topics:
            focus_topics = ["agent", "latency", "evaluation"]

        priority_projects = []
        for project in knowledge.projects:
            haystack = " ".join(
                [
                    project.name,
                    project.business_value,
                    project.architecture,
                    " ".join(module.name for module in project.key_modules),
                ]
            ).lower()
            if any(topic in haystack for topic in focus_topics):
                priority_projects.append(project.name)
        if not priority_projects:
            priority_projects = [project.name for project in knowledge.projects[:2]]

        likely_questions = [
            f"请你用业务结果导向介绍一下 {project_name}。"
            for project_name in priority_projects[:2]
        ]
        likely_questions.extend(
            [
                "你如何平衡效果、延迟和成本？",
                "当 Agent 失败或者工具调用不稳定时，你怎么兜底？",
            ]
        )

        return SessionBriefing(
            company=company,
            business_context=business_context,
            job_description=job_description,
            priority_projects=priority_projects,
            focus_topics=focus_topics,
            style_bias=[
                "先结论后展开",
                "强调真实实现与取舍",
                "对指标、风险和升级路线要有明确表达",
            ],
            likely_questions=likely_questions,
        )
