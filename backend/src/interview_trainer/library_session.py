from __future__ import annotations

import time
from dataclasses import asdict
from uuid import uuid4
from typing import Any

from .briefing import BriefingBuilder
from .library_compile import LibraryCompiler


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


class LibrarySessionBuilder:
    def __init__(
        self,
        *,
        library_compiler: LibraryCompiler | None = None,
        briefing_builder: BriefingBuilder | None = None,
    ) -> None:
        self.library_compiler = library_compiler or LibraryCompiler()
        self.briefing_builder = briefing_builder or BriefingBuilder()

    def build_session_payload(
        self,
        workspace: dict[str, Any],
        preset: dict[str, Any],
        overlay: dict[str, Any] | None,
    ) -> dict[str, Any]:
        knowledge = self._select_knowledge(workspace, preset, overlay)
        bundle = self.library_compiler.compile_workspace(knowledge)
        overlay_payload = overlay or {}
        briefing = self.briefing_builder.build(
            company=_clean_text(overlay_payload.get("company")),
            business_context=_clean_text(overlay_payload.get("business_context")),
            job_description=_clean_text(overlay_payload.get("job_description")),
            knowledge=bundle.compiled_knowledge,
        )
        activation_summary = {
            "bundle_id": str(uuid4()),
            "preset_id": preset["preset_id"],
            "preset_name": preset["name"],
            "overlay_id": _clean_text(preset.get("overlay_id")),
            "overlay_name": _clean_text(overlay_payload.get("name")),
            "project_ids": [project["project_id"] for project in knowledge["projects"]],
            "project_names": [project["name"] for project in knowledge["projects"]],
            "project_count": len(knowledge["projects"]),
            "retrieval_unit_count": len(bundle.retrieval_units),
            "metric_evidence_count": len(bundle.metric_evidence),
            "terminology_count": len(bundle.terminology),
            "built_at": time.time(),
        }
        return {
            "knowledge": knowledge,
            "briefing": asdict(briefing),
            "activation_summary": activation_summary,
        }

    def _select_knowledge(
        self,
        workspace: dict[str, Any],
        preset: dict[str, Any],
        overlay: dict[str, Any] | None,
    ) -> dict[str, Any]:
        knowledge = workspace.get("knowledge", {})
        all_projects = [
            project
            for project in knowledge.get("projects", [])
            if isinstance(project, dict)
        ]
        selected_project_ids = [
            _clean_text(item)
            for item in preset.get("project_ids", [])
            if _clean_text(item)
        ]
        if not selected_project_ids and isinstance(overlay, dict):
            selected_project_ids = [
                _clean_text(item)
                for item in overlay.get("focus_project_ids", [])
                if _clean_text(item)
            ]

        selected_projects = [
            self._build_project_payload(project)
            for project in all_projects
            if not selected_project_ids or project.get("project_id") in selected_project_ids
        ]
        if not selected_projects:
            selected_projects = [
                self._build_project_payload(project)
                for project in all_projects[:1]
            ]

        include_role_documents = bool(preset.get("include_role_documents", True))
        role_documents = knowledge.get("role_documents", []) if include_role_documents else []
        return {
            "profile": dict(knowledge.get("profile", {})),
            "projects": selected_projects,
            "role_documents": [dict(item) for item in role_documents if isinstance(item, dict)],
        }

    def _build_project_payload(self, project: dict[str, Any]) -> dict[str, Any]:
        interviewer_hooks = [
            _clean_text(item)
            for item in project.get("interviewer_hooks", [])
            if _clean_text(item)
        ]
        return {
            "project_id": project["project_id"],
            "name": project["name"],
            "pitch_30": _clean_text(project.get("pitch_30")),
            "pitch_90": _clean_text(project.get("pitch_90")),
            "business_value": _clean_text(project.get("business_value")),
            "architecture": _clean_text(project.get("architecture")),
            "key_metrics": list(project.get("key_metrics", [])),
            "tradeoffs": list(project.get("tradeoffs", [])),
            "failure_cases": list(project.get("failure_cases", [])),
            "limitations": list(project.get("limitations", [])),
            "upgrade_plan": list(project.get("upgrade_plan", [])),
            "interviewer_hooks": interviewer_hooks,
            "follow_up_tree": interviewer_hooks,
            "repo_summaries": [dict(item) for item in project.get("repo_summaries", [])],
            "documents": [dict(item) for item in project.get("documents", [])],
            "code_files": [dict(item) for item in project.get("code_files", [])],
        }
