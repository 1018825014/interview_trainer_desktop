from __future__ import annotations

from dataclasses import asdict
from pathlib import PurePosixPath
from typing import Any

from .types import (
    CodeChunk,
    CodebaseSummary,
    CompiledKnowledge,
    DocChunk,
    ModuleCard,
    ProfileCard,
    ProjectInterviewPack,
    RepoMap,
    RolePlaybook,
)


ROLE_FOCUS_AREAS = [
    "agent orchestration",
    "tool calling",
    "retrieval and reranking",
    "prompt design",
    "evaluation and offline checks",
    "latency, cost and caching",
    "observability and tracing",
    "guardrails and failure recovery",
]


ROLE_ANSWER_FRAMES = [
    "先讲业务目标，再讲系统设计，最后讲评测和线上指标。",
    "先讲当时真实实现，再讲为什么这样取舍，最后讲如果继续做会怎么升级。",
    "回答 Agent 题时优先覆盖工具选择、状态管理、可靠性、成本和人工兜底。",
]


ROLE_FOLLOW_UPS = [
    "如果现在并发翻十倍，你会先改哪一层？",
    "这个方案最容易失败的环节是什么，你怎么监控？",
    "你为什么不选更复杂的一体化方案？",
]


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in cleaned.split("-") if part) or "item"


def _extract_keywords(text: str) -> list[str]:
    words = []
    for raw in text.replace("_", " ").replace("/", " ").replace("-", " ").split():
        token = raw.strip("()[]{}:,.'\"").lower()
        if len(token) >= 4 and token not in words:
            words.append(token)
    return words[:12]


def _split_paragraphs(text: str, prefix: str) -> list[DocChunk]:
    paragraphs = [part.strip() for part in text.replace("\r", "").split("\n\n") if part.strip()]
    chunks: list[DocChunk] = []
    for index, paragraph in enumerate(paragraphs[:6], start=1):
        summary = paragraph.split("。")[0].split(".")[0][:120]
        chunks.append(
            DocChunk(
                chunk_id=f"{prefix}-doc-{index}",
                title=f"{prefix} 文档块 {index}",
                summary=summary or paragraph[:120],
                text=paragraph,
                keywords=_extract_keywords(paragraph),
            )
        )
    if not chunks and text.strip():
        chunks.append(
            DocChunk(
                chunk_id=f"{prefix}-doc-1",
                title=f"{prefix} 文档块 1",
                summary=text[:120],
                text=text.strip(),
                keywords=_extract_keywords(text),
            )
        )
    return chunks


def _chunk_code(path: str, code: str, module_id: str) -> list[CodeChunk]:
    lines = [line.rstrip() for line in code.replace("\r", "").split("\n")]
    window = 40
    chunks: list[CodeChunk] = []
    for index in range(0, len(lines), window):
        window_lines = lines[index : index + window]
        if not any(window_lines):
            continue
        summary_seed = next((line.strip() for line in window_lines if line.strip()), path)
        chunks.append(
            CodeChunk(
                chunk_id=f"{_slugify(path)}-{index // window + 1}",
                path=path,
                summary=summary_seed[:120],
                code="\n".join(window_lines).strip(),
                keywords=_extract_keywords(" ".join(window_lines[:8]) + " " + path),
                module_id=module_id,
            )
        )
    return chunks or [
        CodeChunk(
            chunk_id=f"{_slugify(path)}-1",
            path=path,
            summary=path,
            code=code,
            keywords=_extract_keywords(path),
            module_id=module_id,
        )
    ]


class KnowledgeCompiler:
    """Compiles uploaded profile/docs/code into interview-oriented memory packs."""

    def compile(self, payload: dict[str, Any]) -> CompiledKnowledge:
        profile = self._build_profile(payload.get("profile", {}))
        projects = [
            self._build_project(project_payload)
            for project_payload in payload.get("projects", [])
        ]
        role_playbooks = self._build_role_playbooks(payload.get("role_documents", []))
        terminology = self._build_terminology(profile, projects, role_playbooks)
        return CompiledKnowledge(
            profile_card=profile,
            projects=projects,
            role_playbooks=role_playbooks,
            terminology=terminology,
        )

    def _build_profile(self, payload: dict[str, Any]) -> ProfileCard:
        headline = payload.get("headline", "候选人大模型应用开发工程师")
        return ProfileCard(
            headline=headline,
            strengths=payload.get(
                "strengths",
                [
                    "能把业务问题拆成可落地的 Agent、RAG 和 workflow 系统",
                    "关注效果、延迟、成本和可观测性之间的平衡",
                    "愿意用真实线上取舍解释设计，而不是只背理论答案",
                ],
            ),
            target_roles=payload.get("target_roles", ["AI Agent / LLM 应用开发工程师"]),
            intro_material=payload.get(
                "intro_material",
                [
                    headline,
                    payload.get(
                        "summary",
                        "我擅长把需求拆成检索、推理、编排、评测和观测这些可交付模块。",
                    ),
                ],
            ),
        )

    def _build_project(self, payload: dict[str, Any]) -> ProjectInterviewPack:
        name = payload.get("name", "未命名项目")
        project_id = payload.get("project_id") or _slugify(name)
        source_docs = payload.get("documents", [])
        source_code = payload.get("code_files", [])

        module_cards = self._build_modules(name, source_code, payload.get("modules", []))
        repo_map = self._build_repo_map(source_code, module_cards)
        code_chunks: list[CodeChunk] = []
        for code_file in source_code:
            module_id = self._resolve_module_id(code_file.get("path", ""), module_cards)
            code_chunks.extend(
                _chunk_code(
                    path=code_file.get("path", "unknown.py"),
                    code=code_file.get("content", ""),
                    module_id=module_id,
                )
            )

        doc_chunks: list[DocChunk] = []
        for index, document in enumerate(source_docs, start=1):
            prefix = f"{project_id}-{index}"
            doc_chunks.extend(_split_paragraphs(document.get("content", ""), prefix))

        business_value = payload.get("business_value", "帮助业务团队更快交付 AI 能力。")
        code_summary = self._summarize_codebase(name, module_cards, source_code, repo_map)
        return ProjectInterviewPack(
            project_id=project_id,
            name=name,
            pitch_30=payload.get(
                "pitch_30",
                f"{name} 是一个围绕“{business_value}”搭建的项目，我主要负责把需求拆成稳定可交付的模块，并压住效果和延迟。",
            ),
            pitch_90=payload.get(
                "pitch_90",
                f"{name} 这类项目我会先明确目标场景，再把系统拆成检索、编排、执行和观测几个部分。"
                "真实实现里我更看重可靠性、可调试性和迭代速度，而不是一开始就堆最复杂的方案。",
            ),
            business_value=business_value,
            architecture=payload.get(
                "architecture",
                f"{name} 当前采用清晰分层：入口层接收请求，核心编排层决定工作流，领域模块处理检索、工具调用和输出，"
                "最后用评测和观测闭环。",
            ),
            key_modules=module_cards,
            key_metrics=payload.get("key_metrics", ["优先关注响应延迟、命中率和人工复核成本。"]),
            tradeoffs=payload.get(
                "tradeoffs",
                [
                    "先做可观测、易调试的模块化结构，而不是追求一次性做成全自动黑盒。",
                    "复杂能力拆成可灰度开关的模块，减少线上失败半径。",
                ],
            ),
            failure_cases=payload.get(
                "failure_cases",
                [
                    "检索噪音可能导致回答跑偏，需要通过 rerank 和 evidence 约束收敛。",
                    "链路过长会拖慢延迟，因此把高成本步骤做成按需触发。",
                ],
            ),
            limitations=payload.get(
                "limitations",
                [
                    "复杂长尾场景仍依赖人工兜底或更细的路由策略。",
                    "部分模块为了先交付速度使用启发式规则，后续再考虑学习型优化。",
                ],
            ),
            upgrade_plan=payload.get(
                "upgrade_plan",
                [
                    "把启发式路由升级成结合离线评测的策略路由。",
                    "补强 tracing、反馈学习和更细粒度缓存。",
                ],
            ),
            follow_up_tree=payload.get(
                "follow_up_tree",
                [
                    "为什么你们没有一开始就做 multi-agent？",
                    "这个架构最容易出错的地方在哪？",
                    "如果再给你一个月，你会优先补哪三个能力？",
                ],
            ),
            codebase_summary=code_summary,
            doc_chunks=doc_chunks,
            code_chunks=code_chunks,
        )

    def _build_modules(
        self,
        project_name: str,
        code_files: list[dict[str, Any]],
        manual_modules: list[dict[str, Any]],
    ) -> list[ModuleCard]:
        if manual_modules:
            modules = []
            for item in manual_modules:
                modules.append(
                    ModuleCard(
                        module_id=_slugify(item.get("name", "module")),
                        name=item.get("name", "核心模块"),
                        responsibility=item.get("responsibility", "承接项目中的关键职责。"),
                        interfaces=item.get("interfaces", []),
                        dependencies=item.get("dependencies", []),
                        design_rationale=item.get("design_rationale", "这样拆是为了让模块边界更稳定。"),
                    )
                )
            return modules

        inferred: dict[str, list[str]] = {}
        for code_file in code_files:
            path = code_file.get("path", "")
            pure_path = PurePosixPath(path.replace("\\", "/"))
            parts = [part for part in pure_path.parts if part not in {"src", "app", "backend", "frontend"}]
            bucket = parts[0] if parts else "core"
            inferred.setdefault(bucket, []).append(path)

        modules: list[ModuleCard] = []
        for bucket, paths in list(inferred.items())[:6]:
            module_name = bucket.replace("_", " ").replace("-", " ").title()
            modules.append(
                ModuleCard(
                    module_id=_slugify(f"{project_name}-{bucket}"),
                    name=module_name,
                    responsibility=f"{module_name} 模块负责 {module_name.lower()} 相关能力，并承接 {len(paths)} 个关键文件。",
                    interfaces=[paths[0]],
                    dependencies=sorted(
                        {
                            PurePosixPath(item.replace("\\", "/")).parts[0]
                            for item in paths
                            if PurePosixPath(item.replace("\\", "/")).parts
                        }
                    ),
                    design_rationale="按职责拆分比按技术层拆分更容易在面试时讲清楚边界和取舍。",
                )
            )
        return modules or [
            ModuleCard(
                module_id=f"{_slugify(project_name)}-core",
                name="Core",
                responsibility="项目核心逻辑。",
                interfaces=[],
                dependencies=[],
                design_rationale="先保证核心链路清晰可解释。",
            )
        ]

    def _build_repo_map(self, code_files: list[dict[str, Any]], modules: list[ModuleCard]) -> RepoMap:
        paths = [item.get("path", "") for item in code_files]
        entrypoints = [path for path in paths if path.endswith(("main.py", "app.py", "index.ts", "server.ts"))][:6]
        if not entrypoints:
            entrypoints = paths[:3]
        module_relationships = [
            f"{module.name} -> {', '.join(module.interfaces[:1] or ['internal'])}"
            for module in modules[:6]
        ]
        return RepoMap(
            entrypoints=entrypoints,
            key_paths=paths[:12],
            module_relationships=module_relationships,
            summary="代码库按职责拆分，入口文件负责接线，核心模块负责业务逻辑与数据流。",
        )

    def _summarize_codebase(
        self,
        project_name: str,
        modules: list[ModuleCard],
        code_files: list[dict[str, Any]],
        repo_map: RepoMap,
    ) -> CodebaseSummary:
        languages = {
            PurePosixPath(item.get("path", "").replace("\\", "/")).suffix.lower()
            for item in code_files
        }
        language = ", ".join(sorted(suffix.lstrip(".") or "plain" for suffix in languages if suffix)) or "mixed"
        summary = (
            f"{project_name} 的代码库以 {', '.join(module.name for module in modules[:4])} 为主要模块，"
            "入口层负责接线，核心逻辑集中在少数关键路径，便于面试时从业务目标一路讲到实现细节。"
        )
        return CodebaseSummary(language=language, summary=summary, repo_map=repo_map)

    def _build_role_playbooks(self, role_documents: list[dict[str, Any]]) -> list[RolePlaybook]:
        playbooks = [
            RolePlaybook(
                playbook_id="llm-app-engineer",
                role_name="AI Agent / LLM 应用开发工程师",
                focus_areas=ROLE_FOCUS_AREAS,
                answer_frames=ROLE_ANSWER_FRAMES,
                follow_up_patterns=ROLE_FOLLOW_UPS,
            )
        ]
        for index, document in enumerate(role_documents, start=1):
            text = document.get("content", "")
            extra_focus = _extract_keywords(text)
            playbooks.append(
                RolePlaybook(
                    playbook_id=f"role-doc-{index}",
                    role_name=document.get("title", f"补充岗位资料 {index}"),
                    focus_areas=extra_focus[:8] or ROLE_FOCUS_AREAS[:4],
                    answer_frames=[
                        "先给结论，再补证据和权衡。",
                        "遇到开放题时，用场景、指标、方案、风险、迭代路径来回答。",
                    ],
                    follow_up_patterns=[
                        "这个经验如果放到更大规模场景会怎样？",
                        "你如何证明这个方案优于替代方案？",
                    ],
                )
            )
        return playbooks

    def _build_terminology(
        self,
        profile: ProfileCard,
        projects: list[ProjectInterviewPack],
        role_playbooks: list[RolePlaybook],
    ) -> list[str]:
        terms = list(profile.target_roles)
        terms.extend(profile.strengths)
        for project in projects:
            terms.append(project.name)
            terms.extend(metric.split(" ")[0] for metric in project.key_metrics if metric)
            terms.extend(module.name for module in project.key_modules)
            terms.extend(chunk.path.split("/")[-1] for chunk in project.code_chunks[:12])
        for playbook in role_playbooks:
            terms.extend(playbook.focus_areas)
        deduped = []
        for term in terms:
            clean = term.strip()
            if clean and clean not in deduped:
                deduped.append(clean)
        return deduped[:256]

    def _resolve_module_id(self, path: str, modules: list[ModuleCard]) -> str:
        path_lower = path.lower()
        for module in modules:
            token = module.name.replace(" ", "").lower()
            if token and token in path_lower:
                return module.module_id
        return modules[0].module_id if modules else "core"

    def to_dict(self, knowledge: CompiledKnowledge) -> dict[str, Any]:
        return asdict(knowledge)
