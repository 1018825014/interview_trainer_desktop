from __future__ import annotations

import time
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from .knowledge import KnowledgeCompiler
from .library_compile import LibraryCompiler
from .library_repository import LibraryRepository
from .library_session import LibrarySessionBuilder


CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".sql",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".sh",
}

DOC_EXTENSIONS = {
    ".md",
    ".txt",
    ".rst",
    ".pdf",
}

DEFAULT_PROJECT_DOCUMENT_TITLE = "Project Document"
DEFAULT_ROLE_DOCUMENT_TITLE = "Role Document"


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _content_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


class WorkspaceManager:
    def __init__(
        self,
        compiler: KnowledgeCompiler | None = None,
        storage_root: Path | str | None = None,
    ) -> None:
        self.compiler = compiler or KnowledgeCompiler()
        self.library_compiler = LibraryCompiler(knowledge_compiler=self.compiler)
        self.repository = LibraryRepository(storage_root=storage_root)
        self.session_builder = LibrarySessionBuilder()
        self._workspaces: dict[str, dict[str, Any]] = self.repository.load_workspaces()
        self._upgrade_loaded_workspaces()

    def list_workspaces(self) -> dict[str, Any]:
        workspaces = sorted(
            (self._serialize(workspace) for workspace in self._workspaces.values()),
            key=lambda item: item["updated_at"],
            reverse=True,
        )
        return {"workspaces": workspaces}

    def create_workspace(self, payload: dict[str, Any]) -> dict[str, Any]:
        workspace_id = _clean_text(payload.get("workspace_id")) or str(uuid4())
        now = time.time()
        workspace = {
            "workspace_id": workspace_id,
            "name": _clean_text(payload.get("name")) or "Interview Workspace",
            "knowledge": self._normalize_knowledge_payload(payload.get("knowledge", {})),
            "overlays": [],
            "presets": [],
            "compiled_bundles": [],
            "created_at": now,
            "updated_at": now,
            "compiled_knowledge": None,
            "compile_summary": None,
            "compiled_library_bundle": None,
        }
        self._workspaces[workspace_id] = workspace
        self.repository.save_workspace(workspace)
        return self._serialize(workspace)

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        return self._serialize(workspace)

    def update_workspace(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        if "name" in payload:
            workspace["name"] = _clean_text(payload.get("name")) or workspace["name"]
        if "knowledge" in payload:
            workspace["knowledge"] = self._normalize_knowledge_payload(payload.get("knowledge", {}))
            self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize(workspace)

    def list_projects(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        return {
            "projects": [
                self._serialize_project(project)
                for project in workspace["knowledge"].get("projects", [])
            ]
        }

    def create_project(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        project = self._normalize_project(payload)
        workspace["knowledge"].setdefault("projects", []).append(project)
        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize_project(project)

    def get_project(self, project_id: str) -> dict[str, Any]:
        _, project = self._find_project(project_id)
        return self._serialize_project(project)

    def update_project(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace, project = self._find_project(project_id)
        if "name" in payload:
            project["name"] = _clean_text(payload.get("name")) or project["name"]
        if "pitch_30" in payload:
            project["pitch_30"] = _clean_text(payload.get("pitch_30"))
        if "pitch_90" in payload:
            project["pitch_90"] = _clean_text(payload.get("pitch_90"))
        if "business_value" in payload:
            project["business_value"] = _clean_text(payload.get("business_value")) or project["business_value"]
        if "architecture" in payload:
            project["architecture"] = _clean_text(payload.get("architecture")) or project["architecture"]
        if "key_metrics" in payload:
            project["key_metrics"] = self._normalize_lines(payload.get("key_metrics"))
        if "tradeoffs" in payload:
            project["tradeoffs"] = self._normalize_lines(payload.get("tradeoffs"))
        if "failure_cases" in payload:
            project["failure_cases"] = self._normalize_lines(payload.get("failure_cases"))
        if "limitations" in payload:
            project["limitations"] = self._normalize_lines(payload.get("limitations"))
        if "upgrade_plan" in payload:
            project["upgrade_plan"] = self._normalize_lines(payload.get("upgrade_plan"))
        if "interviewer_hooks" in payload:
            project["interviewer_hooks"] = self._normalize_lines(payload.get("interviewer_hooks"))
        if "manual_evidence" in payload:
            project["manual_evidence"] = [
                self._normalize_manual_evidence(item, index)
                for index, item in enumerate(payload.get("manual_evidence", []), start=1)
                if isinstance(item, dict) and (_clean_text(item.get("title")) or _clean_text(item.get("summary")))
            ]
        if "manual_metrics" in payload:
            project["manual_metrics"] = [
                self._normalize_manual_metric(item, index)
                for index, item in enumerate(payload.get("manual_metrics", []), start=1)
                if isinstance(item, dict) and (_clean_text(item.get("metric_name")) or _clean_text(item.get("metric_value")))
            ]
        if "manual_retrieval_units" in payload:
            project["manual_retrieval_units"] = [
                self._normalize_manual_retrieval_unit(item, index)
                for index, item in enumerate(payload.get("manual_retrieval_units", []), start=1)
                if isinstance(item, dict) and (_clean_text(item.get("short_answer")) or _clean_text(item.get("long_answer")))
            ]
        if "documents" in payload:
            project["documents"] = [
                self._normalize_document_asset(item, scope="project", default_title=f"{DEFAULT_PROJECT_DOCUMENT_TITLE} {index}")
                for index, item in enumerate(payload.get("documents", []), start=1)
                if isinstance(item, dict) and _content_text(item.get("content")).strip()
            ]
        if "code_files" in payload:
            project["code_files"] = [
                self._normalize_code_file(item)
                for item in payload.get("code_files", [])
                if isinstance(item, dict) and _content_text(item.get("content")).strip()
            ]
        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize_project(project)

    def delete_project(self, project_id: str) -> dict[str, str]:
        workspace, project = self._find_project(project_id)
        projects = workspace["knowledge"].get("projects", [])
        workspace["knowledge"]["projects"] = [item for item in projects if item is not project]
        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return {"status": "deleted", "project_id": project_id}

    def list_project_documents(self, project_id: str) -> dict[str, Any]:
        _, project = self._find_project(project_id)
        return {"documents": [self._serialize_document(item) for item in project.get("documents", [])]}

    def create_project_document(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace, project = self._find_project(project_id)
        document = self._normalize_document_asset(payload, scope="project")
        project.setdefault("documents", []).append(document)
        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize_document(document)

    def list_project_repos(self, project_id: str) -> dict[str, Any]:
        _, project = self._find_project(project_id)
        return {"repos": [dict(item) for item in project.get("repo_summaries", [])]}

    def import_project_repo(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace, project = self._find_project(project_id)
        return self._import_into_project(workspace, project, payload)

    def reindex_repo(self, repo_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        workspace, project, repo_summary = self._find_repo(repo_id)
        import_payload = dict(payload or {})
        import_payload.setdefault("path", _clean_text(repo_summary.get("root_path")))
        import_payload.setdefault("project_name", _clean_text(project.get("name")))
        import_payload["repo_id"] = repo_id
        return self._import_into_project(workspace, project, import_payload)

    def list_role_documents(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        return {
            "documents": [
                self._serialize_document(item)
                for item in workspace.get("knowledge", {}).get("role_documents", [])
            ]
        }

    def create_role_document(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        document = self._normalize_document_asset(payload, scope="role")
        workspace.setdefault("knowledge", {}).setdefault("role_documents", []).append(document)
        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize_document(document)

    def update_document(self, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace, document = self._find_document(document_id)
        if "title" in payload:
            document["title"] = _clean_text(payload.get("title")) or document["title"]
        if "path" in payload:
            document["path"] = _clean_text(payload.get("path"))
        if "content" in payload:
            document["content"] = _content_text(payload.get("content"))
        if "source_kind" in payload:
            document["source_kind"] = _clean_text(payload.get("source_kind")) or document["source_kind"]
        if "source_path" in payload:
            document["source_path"] = _clean_text(payload.get("source_path"))
        document["updated_at"] = time.time()
        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = document["updated_at"]
        self.repository.save_workspace(workspace)
        return self._serialize_document(document)

    def delete_document(self, document_id: str) -> dict[str, str]:
        workspace, document = self._find_document(document_id)
        role_documents = workspace.get("knowledge", {}).get("role_documents", [])
        if document in role_documents:
            workspace["knowledge"]["role_documents"] = [item for item in role_documents if item is not document]
        else:
            for project in workspace.get("knowledge", {}).get("projects", []):
                documents = project.get("documents", [])
                if document in documents:
                    project["documents"] = [item for item in documents if item is not document]
                    break
        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return {"status": "deleted", "document_id": document_id}

    def list_overlays(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        return {
            "overlays": [
                self._serialize_overlay(overlay)
                for overlay in workspace.get("overlays", [])
            ]
        }

    def create_overlay(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        overlay = self._normalize_overlay(payload)
        workspace.setdefault("overlays", []).append(overlay)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize_overlay(overlay)

    def get_overlay(self, overlay_id: str) -> dict[str, Any]:
        _, overlay = self._find_overlay(overlay_id)
        return self._serialize_overlay(overlay)

    def update_overlay(self, overlay_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace, overlay = self._find_overlay(overlay_id)
        if "name" in payload:
            overlay["name"] = _clean_text(payload.get("name")) or overlay["name"]
        if "company" in payload:
            overlay["company"] = _clean_text(payload.get("company"))
        if "job_description" in payload:
            overlay["job_description"] = _clean_text(payload.get("job_description"))
        if "business_context" in payload:
            overlay["business_context"] = _clean_text(payload.get("business_context"))
        if "focus_project_ids" in payload:
            overlay["focus_project_ids"] = self._normalize_lines(payload.get("focus_project_ids"))
        if "emphasis_points" in payload:
            overlay["emphasis_points"] = self._normalize_lines(payload.get("emphasis_points"))
        if "style_profile" in payload:
            overlay["style_profile"] = self._normalize_lines(payload.get("style_profile"))
        if "depth_policy" in payload:
            overlay["depth_policy"] = _clean_text(payload.get("depth_policy")) or overlay["depth_policy"]
        overlay["updated_at"] = time.time()
        workspace["updated_at"] = overlay["updated_at"]
        self.repository.save_workspace(workspace)
        return self._serialize_overlay(overlay)

    def list_presets(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        return {
            "presets": [
                self._serialize_preset(preset)
                for preset in workspace.get("presets", [])
            ]
        }

    def create_preset(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        preset = self._normalize_preset(payload)
        workspace.setdefault("presets", []).append(preset)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize_preset(preset)

    def get_preset(self, preset_id: str) -> dict[str, Any]:
        _, preset = self._find_preset(preset_id)
        return self._serialize_preset(preset)

    def update_preset(self, preset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace, preset = self._find_preset(preset_id)
        if "name" in payload:
            preset["name"] = _clean_text(payload.get("name")) or preset["name"]
        if "overlay_id" in payload:
            preset["overlay_id"] = _clean_text(payload.get("overlay_id"))
        if "project_ids" in payload:
            preset["project_ids"] = self._normalize_lines(payload.get("project_ids"))
        if "include_role_documents" in payload:
            preset["include_role_documents"] = bool(payload.get("include_role_documents"))
        preset["updated_at"] = time.time()
        workspace["updated_at"] = preset["updated_at"]
        self.repository.save_workspace(workspace)
        return self._serialize_preset(preset)

    def list_bundles(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        return {
            "bundles": [
                self._serialize_bundle_summary(item)
                for item in workspace.get("compiled_bundles", [])
            ]
        }

    def get_bundle(self, bundle_id: str) -> dict[str, Any]:
        for workspace in self._workspaces.values():
            for bundle in workspace.get("compiled_bundles", []):
                if _clean_text(bundle.get("bundle_id")) == bundle_id:
                    return {
                        **self._serialize_bundle_summary(bundle),
                        "knowledge": bundle.get("knowledge", {}),
                        "briefing": bundle.get("briefing", {}),
                        "artifact_index": dict(bundle.get("artifact_index", {})),
                    }
        raise KeyError(bundle_id)

    def reuse_bundle_session_payload(self, bundle_id: str) -> dict[str, Any]:
        for workspace in self._workspaces.values():
            for bundle in workspace.get("compiled_bundles", []):
                if _clean_text(bundle.get("bundle_id")) != bundle_id:
                    continue
                return {
                    "knowledge": bundle.get("knowledge", {}),
                    "briefing": bundle.get("briefing", {}),
                    "activation_summary": self._serialize_bundle_summary(bundle),
                }
        raise KeyError(bundle_id)

    def compare_bundles(self, left_bundle_id: str, right_bundle_id: str) -> dict[str, Any]:
        left_bundle = self._find_compiled_bundle(left_bundle_id)
        right_bundle = self._find_compiled_bundle(right_bundle_id)
        left_projects = list(left_bundle.get("project_names", []))
        right_projects = list(right_bundle.get("project_names", []))
        added_projects = [item for item in left_projects if item not in right_projects]
        removed_projects = [item for item in right_projects if item not in left_projects]
        left_focus = list(left_bundle.get("briefing", {}).get("focus_topics", []))
        right_focus = list(right_bundle.get("briefing", {}).get("focus_topics", []))
        left_artifacts = self._normalize_bundle_artifact_index(left_bundle.get("artifact_index"))
        right_artifacts = self._normalize_bundle_artifact_index(right_bundle.get("artifact_index"))
        return {
            "left_bundle": self._serialize_bundle_summary(left_bundle),
            "right_bundle": self._serialize_bundle_summary(right_bundle),
            "added_projects": added_projects,
            "removed_projects": removed_projects,
            "project_count_delta": int(left_bundle.get("project_count", 0)) - int(right_bundle.get("project_count", 0)),
            "retrieval_unit_delta": int(left_bundle.get("retrieval_unit_count", 0))
            - int(right_bundle.get("retrieval_unit_count", 0)),
            "metric_evidence_delta": int(left_bundle.get("metric_evidence_count", 0))
            - int(right_bundle.get("metric_evidence_count", 0)),
            "terminology_delta": int(left_bundle.get("terminology_count", 0))
            - int(right_bundle.get("terminology_count", 0)),
            "added_focus_topics": [item for item in left_focus if item not in right_focus],
            "removed_focus_topics": [item for item in right_focus if item not in left_focus],
            "added_retrieval_units": [
                item for item in left_artifacts["retrieval_units"] if item not in right_artifacts["retrieval_units"]
            ],
            "removed_retrieval_units": [
                item for item in right_artifacts["retrieval_units"] if item not in left_artifacts["retrieval_units"]
            ],
            "added_evidence_titles": [
                item for item in left_artifacts["evidence_titles"] if item not in right_artifacts["evidence_titles"]
            ],
            "removed_evidence_titles": [
                item for item in right_artifacts["evidence_titles"] if item not in left_artifacts["evidence_titles"]
            ],
            "added_hook_texts": [item for item in left_artifacts["hook_texts"] if item not in right_artifacts["hook_texts"]],
            "removed_hook_texts": [item for item in right_artifacts["hook_texts"] if item not in left_artifacts["hook_texts"]],
        }

    def get_workspace_compiled_preview(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        preview = workspace.get("compiled_library_bundle")
        if not isinstance(preview, dict):
            return self._empty_compiled_preview()
        return {
            "compiled": True,
            "module_cards": [dict(item) for item in preview.get("module_cards", [])],
            "evidence_cards": [dict(item) for item in preview.get("evidence_cards", [])],
            "metric_evidence": [dict(item) for item in preview.get("metric_evidence", [])],
            "retrieval_units": [dict(item) for item in preview.get("retrieval_units", [])],
            "terminology": list(preview.get("terminology", [])),
            "compiled_at": float(preview.get("compiled_at", 0.0) or 0.0),
        }

    def get_project_compiled_preview(self, project_id: str) -> dict[str, Any]:
        workspace, project = self._find_project(project_id)
        preview = self.get_workspace_compiled_preview(workspace["workspace_id"])
        if not preview.get("compiled"):
            return {
                "compiled": False,
                "project_id": project["project_id"],
                "project_name": project["name"],
                "module_cards": [],
                "evidence_cards": [],
                "metric_evidence": [],
                "retrieval_units": [],
                "terminology": [],
                "compiled_at": 0.0,
            }
        return {
            "compiled": True,
            "project_id": project["project_id"],
            "project_name": project["name"],
            "module_cards": [
                dict(item)
                for item in preview.get("module_cards", [])
                if _clean_text(item.get("project_id")) == project_id
            ],
            "evidence_cards": [
                dict(item)
                for item in preview.get("evidence_cards", [])
                if _clean_text(item.get("project_id")) == project_id
            ],
            "metric_evidence": [
                dict(item)
                for item in preview.get("metric_evidence", [])
                if _clean_text(item.get("project_id")) == project_id
            ],
            "retrieval_units": [
                dict(item)
                for item in preview.get("retrieval_units", [])
                if _clean_text(item.get("project_id")) == project_id
            ],
            "terminology": list(preview.get("terminology", [])),
            "compiled_at": float(preview.get("compiled_at", 0.0) or 0.0),
        }

    def build_preset_session_payload(self, preset_id: str) -> dict[str, Any]:
        workspace, preset = self._find_preset(preset_id)
        overlay = None
        overlay_id = _clean_text(preset.get("overlay_id"))
        if overlay_id:
            try:
                _, overlay = self._find_overlay(overlay_id)
            except KeyError:
                overlay = None
        payload = self.session_builder.build_session_payload(workspace, preset, overlay)
        bundle_record = {
            **dict(payload["activation_summary"]),
            "knowledge": payload.get("knowledge", {}),
            "briefing": payload.get("briefing", {}),
            "artifact_index": self._normalize_bundle_artifact_index(payload.get("artifact_index")),
        }
        workspace.setdefault("compiled_bundles", []).append(bundle_record)
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return payload

    def compile_workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        bundle = self.library_compiler.compile_workspace(workspace["knowledge"])
        compiled = bundle.compiled_knowledge
        workspace["compiled_knowledge"] = self.compiler.to_dict(compiled)
        workspace["compiled_library_bundle"] = self._serialize_compiled_library_bundle(bundle)
        workspace["compile_summary"] = {
            "projects": [project.name for project in compiled.projects],
            "role_playbooks": [playbook.role_name for playbook in compiled.role_playbooks],
            "terminology_count": len(compiled.terminology),
            "modules": sum(len(project.key_modules) for project in compiled.projects),
            "doc_chunks": sum(len(project.doc_chunks) for project in compiled.projects),
            "code_chunks": sum(len(project.code_chunks) for project in compiled.projects),
        }
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize(workspace)

    def import_path(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        root = Path(_clean_text(payload.get("path"))).expanduser()
        if not root.exists():
            raise FileNotFoundError(f"Path not found: {root}")
        project_name = _clean_text(payload.get("project_name")) or root.name or "Imported Project"
        projects = workspace["knowledge"].setdefault("projects", [])
        project = next((item for item in projects if _clean_text(item.get("name")) == project_name), None)
        if project is None:
            project = self._default_project(project_name)
            projects.append(project)
        return self._import_into_project(workspace, project, payload)

    def _serialize(self, workspace: dict[str, Any]) -> dict[str, Any]:
        return {
            "workspace_id": workspace["workspace_id"],
            "name": workspace["name"],
            "knowledge": {
                **workspace["knowledge"],
                "projects": [
                    self._serialize_project(project)
                    for project in workspace["knowledge"].get("projects", [])
                ],
                "role_documents": [
                    self._serialize_document(item)
                    for item in workspace["knowledge"].get("role_documents", [])
                ],
            },
            "overlays": [self._serialize_overlay(item) for item in workspace.get("overlays", [])],
            "presets": [self._serialize_preset(item) for item in workspace.get("presets", [])],
            "compiled_bundles": [
                self._serialize_bundle_summary(item)
                for item in workspace.get("compiled_bundles", [])
            ],
            "created_at": workspace["created_at"],
            "updated_at": workspace["updated_at"],
            "compiled_knowledge": workspace["compiled_knowledge"],
            "compile_summary": workspace["compile_summary"],
        }

    def _normalize_knowledge_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile_input = payload.get("profile", {}) if isinstance(payload, dict) else {}
        projects_input = payload.get("projects", []) if isinstance(payload, dict) else []
        role_documents_input = payload.get("role_documents", []) if isinstance(payload, dict) else []
        return {
            "profile": {
                "headline": _clean_text(profile_input.get("headline")) or "LLM application engineer",
                "summary": _clean_text(profile_input.get("summary")),
                "strengths": self._normalize_lines(profile_input.get("strengths")),
                "target_roles": self._normalize_lines(profile_input.get("target_roles")),
                "intro_material": self._normalize_lines(profile_input.get("intro_material")),
            },
            "projects": [
                self._normalize_project(project_input)
                for project_input in projects_input
                if isinstance(project_input, dict)
            ],
            "role_documents": [
                self._normalize_document_asset(document, scope="role", default_title=f"{DEFAULT_ROLE_DOCUMENT_TITLE} {index}")
                for index, document in enumerate(role_documents_input, start=1)
                if isinstance(document, dict) and _content_text(document.get("content")).strip()
            ],
        }

    def _normalize_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        project = self._default_project(_clean_text(payload.get("name")) or "Interview Project")
        project["project_id"] = _clean_text(payload.get("project_id")) or project["project_id"]
        project["pitch_30"] = _clean_text(payload.get("pitch_30")) or project["pitch_30"]
        project["pitch_90"] = _clean_text(payload.get("pitch_90")) or project["pitch_90"]
        project["business_value"] = _clean_text(payload.get("business_value")) or project["business_value"]
        project["architecture"] = _clean_text(payload.get("architecture")) or project["architecture"]
        project["key_metrics"] = self._normalize_lines(payload.get("key_metrics")) or project["key_metrics"]
        project["tradeoffs"] = self._normalize_lines(payload.get("tradeoffs")) or project["tradeoffs"]
        project["failure_cases"] = self._normalize_lines(payload.get("failure_cases")) or project["failure_cases"]
        project["limitations"] = self._normalize_lines(payload.get("limitations")) or project["limitations"]
        project["upgrade_plan"] = self._normalize_lines(payload.get("upgrade_plan")) or project["upgrade_plan"]
        project["interviewer_hooks"] = self._normalize_lines(payload.get("interviewer_hooks")) or project["interviewer_hooks"]
        project["manual_evidence"] = [
            self._normalize_manual_evidence(item, index)
            for index, item in enumerate(payload.get("manual_evidence", []), start=1)
            if isinstance(item, dict) and (_clean_text(item.get("title")) or _clean_text(item.get("summary")))
        ]
        project["manual_metrics"] = [
            self._normalize_manual_metric(item, index)
            for index, item in enumerate(payload.get("manual_metrics", []), start=1)
            if isinstance(item, dict) and (_clean_text(item.get("metric_name")) or _clean_text(item.get("metric_value")))
        ]
        project["manual_retrieval_units"] = [
            self._normalize_manual_retrieval_unit(item, index)
            for index, item in enumerate(payload.get("manual_retrieval_units", []), start=1)
            if isinstance(item, dict) and (_clean_text(item.get("short_answer")) or _clean_text(item.get("long_answer")))
        ]
        project["repo_summaries"] = [
            {
                "repo_id": _clean_text(item.get("repo_id")) or str(uuid4()),
                "label": _clean_text(item.get("label")) or _clean_text(item.get("root_path")) or "Imported Repo",
                "root_path": _clean_text(item.get("root_path")),
                "status": _clean_text(item.get("status")) or "ready",
                "last_scanned_at": float(item.get("last_scanned_at", 0.0) or 0.0),
                "imported_docs": int(item.get("imported_docs", 0) or 0),
                "imported_code_files": int(item.get("imported_code_files", 0) or 0),
            }
            for item in payload.get("repo_summaries", [])
            if isinstance(item, dict) and _clean_text(item.get("root_path"))
        ]
        project["documents"] = [
            self._normalize_document_asset(item, scope="project", default_title=f"{DEFAULT_PROJECT_DOCUMENT_TITLE} {index}")
            for index, item in enumerate(payload.get("documents", []), start=1)
            if isinstance(item, dict) and _content_text(item.get("content")).strip()
        ]
        project["code_files"] = [
            self._normalize_code_file(item)
            for item in payload.get("code_files", [])
            if isinstance(item, dict) and _content_text(item.get("content")).strip()
        ]
        return project

    def _default_project(self, name: str) -> dict[str, Any]:
        return {
            "project_id": str(uuid4()),
            "name": name,
            "pitch_30": "",
            "pitch_90": "",
            "business_value": "",
            "architecture": "",
            "key_metrics": [],
            "tradeoffs": [],
            "failure_cases": [],
            "limitations": [],
            "upgrade_plan": [],
            "interviewer_hooks": [],
            "manual_evidence": [],
            "manual_metrics": [],
            "manual_retrieval_units": [],
            "repo_summaries": [],
            "documents": [],
            "code_files": [],
        }

    def _serialize_project(self, project: dict[str, Any]) -> dict[str, Any]:
        return {
            "project_id": project["project_id"],
            "name": project["name"],
            "pitch_30": project.get("pitch_30", ""),
            "pitch_90": project.get("pitch_90", ""),
            "business_value": project["business_value"],
            "architecture": project["architecture"],
            "key_metrics": list(project.get("key_metrics", [])),
            "tradeoffs": list(project.get("tradeoffs", [])),
            "failure_cases": list(project.get("failure_cases", [])),
            "limitations": list(project.get("limitations", [])),
            "upgrade_plan": list(project.get("upgrade_plan", [])),
            "interviewer_hooks": list(project.get("interviewer_hooks", [])),
            "manual_evidence": [self._serialize_manual_evidence(item) for item in project.get("manual_evidence", [])],
            "manual_metrics": [self._serialize_manual_metric(item) for item in project.get("manual_metrics", [])],
            "manual_retrieval_units": [
                self._serialize_manual_retrieval_unit(item)
                for item in project.get("manual_retrieval_units", [])
            ],
            "repo_summaries": [dict(item) for item in project.get("repo_summaries", [])],
            "documents": [self._serialize_document(item) for item in project.get("documents", [])],
            "code_files": [self._serialize_code_file(item) for item in project.get("code_files", [])],
        }

    def _normalize_overlay(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        return {
            "overlay_id": _clean_text(payload.get("overlay_id")) or str(uuid4()),
            "name": _clean_text(payload.get("name")) or "Interview Overlay",
            "company": _clean_text(payload.get("company")),
            "job_description": _clean_text(payload.get("job_description")),
            "business_context": _clean_text(payload.get("business_context")),
            "focus_project_ids": self._normalize_lines(payload.get("focus_project_ids")),
            "emphasis_points": self._normalize_lines(payload.get("emphasis_points")),
            "style_profile": self._normalize_lines(payload.get("style_profile")),
            "depth_policy": _clean_text(payload.get("depth_policy")) or "standard",
            "created_at": float(payload.get("created_at", now) or now),
            "updated_at": float(payload.get("updated_at", now) or now),
        }

    def _serialize_overlay(self, overlay: dict[str, Any]) -> dict[str, Any]:
        return {
            "overlay_id": overlay["overlay_id"],
            "name": overlay["name"],
            "company": overlay.get("company", ""),
            "job_description": overlay.get("job_description", ""),
            "business_context": overlay.get("business_context", ""),
            "focus_project_ids": list(overlay.get("focus_project_ids", [])),
            "emphasis_points": list(overlay.get("emphasis_points", [])),
            "style_profile": list(overlay.get("style_profile", [])),
            "depth_policy": overlay.get("depth_policy", "standard"),
            "created_at": overlay.get("created_at", 0.0),
            "updated_at": overlay.get("updated_at", 0.0),
        }

    def _normalize_preset(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        return {
            "preset_id": _clean_text(payload.get("preset_id")) or str(uuid4()),
            "name": _clean_text(payload.get("name")) or "Interview Preset",
            "overlay_id": _clean_text(payload.get("overlay_id")),
            "project_ids": self._normalize_lines(payload.get("project_ids")),
            "include_role_documents": bool(payload.get("include_role_documents", True)),
            "created_at": float(payload.get("created_at", now) or now),
            "updated_at": float(payload.get("updated_at", now) or now),
        }

    def _serialize_preset(self, preset: dict[str, Any]) -> dict[str, Any]:
        return {
            "preset_id": preset["preset_id"],
            "name": preset["name"],
            "overlay_id": preset.get("overlay_id", ""),
            "project_ids": list(preset.get("project_ids", [])),
            "include_role_documents": bool(preset.get("include_role_documents", True)),
            "created_at": preset.get("created_at", 0.0),
            "updated_at": preset.get("updated_at", 0.0),
        }

    def _normalize_lines(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [text for text in (_clean_text(item) for item in value) if text]
        if isinstance(value, str):
            return [line.strip() for line in value.replace("\r", "").split("\n") if line.strip()]
        return []

    def _normalize_document_asset(
        self,
        payload: dict[str, Any],
        *,
        scope: str,
        default_title: str | None = None,
    ) -> dict[str, Any]:
        path = _clean_text(payload.get("path"))
        title = _clean_text(payload.get("title")) or (Path(path).name if path else "") or (default_title or DEFAULT_PROJECT_DOCUMENT_TITLE)
        now = time.time()
        return {
            "document_id": _clean_text(payload.get("document_id")) or str(uuid4()),
            "scope": scope,
            "title": title,
            "path": path,
            "content": _content_text(payload.get("content")),
            "source_kind": _clean_text(payload.get("source_kind")) or "manual",
            "source_path": _clean_text(payload.get("source_path")),
            "repo_id": _clean_text(payload.get("repo_id")),
            "updated_at": float(payload.get("updated_at", now) or now),
        }

    def _serialize_document(self, document: dict[str, Any]) -> dict[str, Any]:
        return {
            "document_id": document.get("document_id", ""),
            "scope": document.get("scope", "project"),
            "title": document.get("title", ""),
            "path": document.get("path", ""),
            "content": document.get("content", ""),
            "source_kind": document.get("source_kind", "manual"),
            "source_path": document.get("source_path", ""),
            "repo_id": document.get("repo_id", ""),
            "updated_at": document.get("updated_at", 0.0),
        }

    def _normalize_code_file(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "path": _clean_text(payload.get("path")) or "src/main.py",
            "content": _content_text(payload.get("content")),
            "source_kind": _clean_text(payload.get("source_kind")) or "manual",
            "source_path": _clean_text(payload.get("source_path")),
            "repo_id": _clean_text(payload.get("repo_id")),
        }

    def _serialize_code_file(self, code_file: dict[str, Any]) -> dict[str, Any]:
        return {
            "path": code_file.get("path", "src/main.py"),
            "content": code_file.get("content", ""),
            "source_kind": code_file.get("source_kind", "manual"),
            "source_path": code_file.get("source_path", ""),
            "repo_id": code_file.get("repo_id", ""),
        }

    def _serialize_compiled_library_bundle(self, bundle: Any) -> dict[str, Any]:
        payload = bundle.to_dict()
        return {
            "module_cards": [dict(item) for item in payload.get("module_cards", [])],
            "evidence_cards": [dict(item) for item in payload.get("evidence_cards", [])],
            "metric_evidence": [dict(item) for item in payload.get("metric_evidence", [])],
            "retrieval_units": [dict(item) for item in payload.get("retrieval_units", [])],
            "terminology": list(payload.get("terminology", [])),
            "compiled_at": time.time(),
        }

    def _serialize_bundle_summary(self, bundle: dict[str, Any]) -> dict[str, Any]:
        return {
            "bundle_id": _clean_text(bundle.get("bundle_id")),
            "preset_id": _clean_text(bundle.get("preset_id")),
            "preset_name": _clean_text(bundle.get("preset_name")),
            "overlay_id": _clean_text(bundle.get("overlay_id")),
            "overlay_name": _clean_text(bundle.get("overlay_name")),
            "project_ids": list(bundle.get("project_ids", [])),
            "project_names": list(bundle.get("project_names", [])),
            "project_count": int(bundle.get("project_count", 0) or 0),
            "retrieval_unit_count": int(bundle.get("retrieval_unit_count", 0) or 0),
            "metric_evidence_count": int(bundle.get("metric_evidence_count", 0) or 0),
            "terminology_count": int(bundle.get("terminology_count", 0) or 0),
            "built_at": float(bundle.get("built_at", 0.0) or 0.0),
        }

    def _normalize_bundle_artifact_index(self, payload: Any) -> dict[str, list[str]]:
        raw = payload if isinstance(payload, dict) else {}
        return {
            "retrieval_units": self._normalize_lines(raw.get("retrieval_units")),
            "evidence_titles": self._normalize_lines(raw.get("evidence_titles")),
            "metric_names": self._normalize_lines(raw.get("metric_names")),
            "hook_texts": self._normalize_lines(raw.get("hook_texts")),
        }

    def _find_compiled_bundle(self, bundle_id: str) -> dict[str, Any]:
        for workspace in self._workspaces.values():
            for bundle in workspace.get("compiled_bundles", []):
                if _clean_text(bundle.get("bundle_id")) == bundle_id:
                    return bundle
        raise KeyError(bundle_id)

    def _empty_compiled_preview(self) -> dict[str, Any]:
        return {
            "compiled": False,
            "module_cards": [],
            "evidence_cards": [],
            "metric_evidence": [],
            "retrieval_units": [],
            "terminology": [],
            "compiled_at": 0.0,
        }

    def _invalidate_compiled_artifacts(self, workspace: dict[str, Any]) -> None:
        workspace["compiled_knowledge"] = None
        workspace["compile_summary"] = None
        workspace["compiled_library_bundle"] = None

    def _normalize_manual_evidence(self, payload: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "evidence_id": _clean_text(payload.get("evidence_id")) or f"manual-evidence-{index}",
            "module_id": _clean_text(payload.get("module_id")) or None,
            "evidence_type": _clean_text(payload.get("evidence_type")) or "manual_note",
            "title": _clean_text(payload.get("title")) or f"Evidence {index}",
            "summary": _clean_text(payload.get("summary")),
            "source_kind": _clean_text(payload.get("source_kind")) or "manual_note",
            "source_ref": _clean_text(payload.get("source_ref")) or "workspace note",
            "confidence": _clean_text(payload.get("confidence")) or "medium",
        }

    def _serialize_manual_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": evidence.get("evidence_id", ""),
            "module_id": evidence.get("module_id"),
            "evidence_type": evidence.get("evidence_type", "manual_note"),
            "title": evidence.get("title", ""),
            "summary": evidence.get("summary", ""),
            "source_kind": evidence.get("source_kind", "manual_note"),
            "source_ref": evidence.get("source_ref", ""),
            "confidence": evidence.get("confidence", "medium"),
        }

    def _normalize_manual_metric(self, payload: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "evidence_id": _clean_text(payload.get("evidence_id")) or f"manual-metric-{index}",
            "module_id": _clean_text(payload.get("module_id")) or None,
            "metric_name": _clean_text(payload.get("metric_name")) or f"metric_{index}",
            "metric_value": _clean_text(payload.get("metric_value")),
            "baseline": _clean_text(payload.get("baseline")),
            "method": _clean_text(payload.get("method")) or "manual note",
            "environment": _clean_text(payload.get("environment")) or "workspace",
            "source_note": _clean_text(payload.get("source_note")) or "manual metric",
            "confidence": _clean_text(payload.get("confidence")) or "medium",
        }

    def _serialize_manual_metric(self, metric: dict[str, Any]) -> dict[str, Any]:
        return {
            "evidence_id": metric.get("evidence_id", ""),
            "module_id": metric.get("module_id"),
            "metric_name": metric.get("metric_name", ""),
            "metric_value": metric.get("metric_value", ""),
            "baseline": metric.get("baseline", ""),
            "method": metric.get("method", "manual note"),
            "environment": metric.get("environment", "workspace"),
            "source_note": metric.get("source_note", ""),
            "confidence": metric.get("confidence", "medium"),
        }

    def _normalize_manual_retrieval_unit(self, payload: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "unit_id": _clean_text(payload.get("unit_id")) or f"manual-ru-{index}",
            "unit_type": _clean_text(payload.get("unit_type")) or "project_intro",
            "module_id": _clean_text(payload.get("module_id")) or None,
            "question_forms": self._normalize_lines(payload.get("question_forms")),
            "short_answer": _clean_text(payload.get("short_answer")),
            "long_answer": _clean_text(payload.get("long_answer")),
            "key_points": self._normalize_lines(payload.get("key_points")),
            "supporting_refs": self._normalize_lines(payload.get("supporting_refs")),
            "hooks": self._normalize_lines(payload.get("hooks")),
            "safe_claims": self._normalize_lines(payload.get("safe_claims")),
        }

    def _serialize_manual_retrieval_unit(self, unit: dict[str, Any]) -> dict[str, Any]:
        return {
            "unit_id": unit.get("unit_id", ""),
            "unit_type": unit.get("unit_type", "project_intro"),
            "module_id": unit.get("module_id"),
            "question_forms": list(unit.get("question_forms", [])),
            "short_answer": unit.get("short_answer", ""),
            "long_answer": unit.get("long_answer", ""),
            "key_points": list(unit.get("key_points", [])),
            "supporting_refs": list(unit.get("supporting_refs", [])),
            "hooks": list(unit.get("hooks", [])),
            "safe_claims": list(unit.get("safe_claims", [])),
        }

    def _relative_path(self, root: Path, file_path: Path) -> str:
        if root.is_file():
            return root.name
        try:
            relative = file_path.relative_to(root)
        except ValueError:
            relative = file_path
        return PurePosixPath(relative.as_posix()).as_posix()

    def _find_project(self, project_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for workspace in self._workspaces.values():
            for project in workspace.get("knowledge", {}).get("projects", []):
                if _clean_text(project.get("project_id")) == project_id:
                    return workspace, project
        raise KeyError(project_id)

    def _find_overlay(self, overlay_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for workspace in self._workspaces.values():
            for overlay in workspace.get("overlays", []):
                if _clean_text(overlay.get("overlay_id")) == overlay_id:
                    return workspace, overlay
        raise KeyError(overlay_id)

    def _find_preset(self, preset_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for workspace in self._workspaces.values():
            for preset in workspace.get("presets", []):
                if _clean_text(preset.get("preset_id")) == preset_id:
                    return workspace, preset
        raise KeyError(preset_id)

    def _find_document(self, document_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for workspace in self._workspaces.values():
            for document in workspace.get("knowledge", {}).get("role_documents", []):
                if _clean_text(document.get("document_id")) == document_id:
                    return workspace, document
            for project in workspace.get("knowledge", {}).get("projects", []):
                for document in project.get("documents", []):
                    if _clean_text(document.get("document_id")) == document_id:
                        return workspace, document
        raise KeyError(document_id)

    def _find_repo(self, repo_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        for workspace in self._workspaces.values():
            for project in workspace.get("knowledge", {}).get("projects", []):
                for repo_summary in project.get("repo_summaries", []):
                    if _clean_text(repo_summary.get("repo_id")) == repo_id:
                        return workspace, project, repo_summary
        raise KeyError(repo_id)

    def _import_into_project(
        self,
        workspace: dict[str, Any],
        project: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        root = Path(_clean_text(payload.get("path"))).expanduser()
        if not root.exists():
            raise FileNotFoundError(f"Path not found: {root}")

        project_name = _clean_text(payload.get("project_name")) or _clean_text(project.get("name")) or root.name or "Imported Project"
        requested_repo_id = _clean_text(payload.get("repo_id"))
        max_files = max(1, int(payload.get("max_files", 80)))
        max_chars = max(200, int(payload.get("max_chars_per_file", 12000)))
        docs: list[dict[str, Any]] = []
        code_files: list[dict[str, Any]] = []
        repo_summaries = project.setdefault("repo_summaries", [])
        existing_repo = next(
            (
                item
                for item in repo_summaries
                if (requested_repo_id and _clean_text(item.get("repo_id")) == requested_repo_id)
                or _clean_text(item.get("root_path")) == str(root)
            ),
            None,
        )
        repo_id = _clean_text(existing_repo.get("repo_id")) if isinstance(existing_repo, dict) else requested_repo_id or str(uuid4())

        files = [root] if root.is_file() else sorted(item for item in root.rglob("*") if item.is_file())
        for file_path in files:
            if file_path.name.startswith(".") and file_path.name not in {".env.example"}:
                continue
            suffix = file_path.suffix.lower()
            if suffix not in CODE_EXTENSIONS and suffix not in DOC_EXTENSIONS:
                continue
            if len(docs) + len(code_files) >= max_files:
                break
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not text.strip():
                continue
            relative_path = self._relative_path(root, file_path)
            if len(text) > max_chars:
                text = text[:max_chars] + "\n... [truncated]"
            if suffix in DOC_EXTENSIONS:
                docs.append(
                    self._normalize_document_asset(
                        {
                            "title": Path(relative_path).name,
                            "path": relative_path,
                            "content": text,
                            "source_kind": "repo_import",
                            "source_path": str(root),
                            "repo_id": repo_id,
                        },
                        scope="project",
                    )
                )
            else:
                code_files.append(
                    self._normalize_code_file(
                        {
                            "path": relative_path,
                            "content": text,
                            "source_kind": "repo_import",
                            "source_path": str(root),
                            "repo_id": repo_id,
                        }
                    )
                )

        project["name"] = project_name or project.get("name", "")
        project["documents"] = [
            item for item in project.get("documents", [])
            if not self._is_repo_managed_document(item, repo_id)
        ] + docs
        project["code_files"] = [
            item for item in project.get("code_files", [])
            if not self._is_repo_managed_code_file(item, repo_id)
        ] + code_files
        if "business_value" in payload:
            project["business_value"] = _clean_text(payload.get("business_value")) or project.get("business_value", "")
        if "architecture" in payload:
            project["architecture"] = _clean_text(payload.get("architecture")) or project.get("architecture", "")

        self._invalidate_compiled_artifacts(workspace)
        workspace["updated_at"] = time.time()
        repo_summary = {
            "repo_id": repo_id,
            "label": project_name,
            "root_path": str(root),
            "status": "ready",
            "last_scanned_at": workspace["updated_at"],
            "imported_docs": len(docs),
            "imported_code_files": len(code_files),
        }
        if isinstance(existing_repo, dict):
            existing_repo.update(repo_summary)
        else:
            repo_summaries.append(repo_summary)
        self.repository.save_workspace(workspace)

        result = self._serialize(workspace)
        result["import_summary"] = {
            "project_name": project_name,
            "imported_docs": len(docs),
            "imported_code_files": len(code_files),
            "source_path": str(root),
        }
        return result

    def _is_repo_managed_document(self, document: dict[str, Any], repo_id: str) -> bool:
        return _clean_text(document.get("source_kind")) == "repo_import" and _clean_text(document.get("repo_id")) == repo_id

    def _is_repo_managed_code_file(self, code_file: dict[str, Any], repo_id: str) -> bool:
        return _clean_text(code_file.get("source_kind")) == "repo_import" and _clean_text(code_file.get("repo_id")) == repo_id

    def _upgrade_loaded_workspaces(self) -> None:
        changed = False
        for workspace in self._workspaces.values():
            if "overlays" not in workspace:
                workspace["overlays"] = []
                changed = True
            else:
                normalized_overlays = [
                    self._normalize_overlay(overlay)
                    for overlay in workspace.get("overlays", [])
                    if isinstance(overlay, dict)
                ]
                if normalized_overlays != workspace.get("overlays", []):
                    workspace["overlays"] = normalized_overlays
                    changed = True
            if "presets" not in workspace:
                workspace["presets"] = []
                changed = True
            else:
                normalized_presets = [
                    self._normalize_preset(preset)
                    for preset in workspace.get("presets", [])
                    if isinstance(preset, dict)
                ]
                if normalized_presets != workspace.get("presets", []):
                    workspace["presets"] = normalized_presets
                    changed = True
            if "compiled_bundles" not in workspace:
                workspace["compiled_bundles"] = []
                changed = True
            else:
                normalized_bundles = []
                for bundle in workspace.get("compiled_bundles", []):
                    if not isinstance(bundle, dict):
                        continue
                    normalized = dict(bundle)
                    normalized["artifact_index"] = self._normalize_bundle_artifact_index(bundle.get("artifact_index"))
                    normalized_bundles.append(normalized)
                if normalized_bundles != workspace.get("compiled_bundles", []):
                    workspace["compiled_bundles"] = normalized_bundles
                    changed = True
            if "compiled_library_bundle" not in workspace:
                workspace["compiled_library_bundle"] = None
                changed = True
            normalized_role_documents = [
                self._normalize_document_asset(document, scope="role", default_title=f"{DEFAULT_ROLE_DOCUMENT_TITLE} {index}")
                for index, document in enumerate(workspace.get("knowledge", {}).get("role_documents", []), start=1)
                if isinstance(document, dict) and _content_text(document.get("content")).strip()
            ]
            if normalized_role_documents != workspace.get("knowledge", {}).get("role_documents", []):
                workspace.setdefault("knowledge", {})["role_documents"] = normalized_role_documents
                changed = True
            for project in workspace.get("knowledge", {}).get("projects", []):
                if not _clean_text(project.get("project_id")):
                    project["project_id"] = str(uuid4())
                    changed = True
                for field in (
                    "pitch_30",
                    "pitch_90",
                    "key_metrics",
                    "tradeoffs",
                    "failure_cases",
                    "limitations",
                    "upgrade_plan",
                    "interviewer_hooks",
                    "manual_evidence",
                    "manual_metrics",
                    "manual_retrieval_units",
                ):
                    if field not in project:
                        project[field] = [] if field.endswith("s") or field in {
                            "key_metrics",
                            "tradeoffs",
                            "manual_evidence",
                            "manual_metrics",
                            "manual_retrieval_units",
                        } else ""
                        changed = True
                if not isinstance(project.get("key_metrics"), list):
                    project["key_metrics"] = self._normalize_lines(project.get("key_metrics"))
                    changed = True
                for field in (
                    "tradeoffs",
                    "failure_cases",
                    "limitations",
                    "upgrade_plan",
                    "interviewer_hooks",
                ):
                    if not isinstance(project.get(field), list):
                        project[field] = self._normalize_lines(project.get(field))
                        changed = True
                normalized_manual_evidence = [
                    self._normalize_manual_evidence(item, index)
                    for index, item in enumerate(project.get("manual_evidence", []), start=1)
                    if isinstance(item, dict) and (_clean_text(item.get("title")) or _clean_text(item.get("summary")))
                ]
                if normalized_manual_evidence != project.get("manual_evidence", []):
                    project["manual_evidence"] = normalized_manual_evidence
                    changed = True
                normalized_manual_metrics = [
                    self._normalize_manual_metric(item, index)
                    for index, item in enumerate(project.get("manual_metrics", []), start=1)
                    if isinstance(item, dict) and (_clean_text(item.get("metric_name")) or _clean_text(item.get("metric_value")))
                ]
                if normalized_manual_metrics != project.get("manual_metrics", []):
                    project["manual_metrics"] = normalized_manual_metrics
                    changed = True
                normalized_manual_units = [
                    self._normalize_manual_retrieval_unit(item, index)
                    for index, item in enumerate(project.get("manual_retrieval_units", []), start=1)
                    if isinstance(item, dict) and (_clean_text(item.get("short_answer")) or _clean_text(item.get("long_answer")))
                ]
                if normalized_manual_units != project.get("manual_retrieval_units", []):
                    project["manual_retrieval_units"] = normalized_manual_units
                    changed = True
                if "repo_summaries" not in project:
                    project["repo_summaries"] = []
                    changed = True
                normalized_documents = [
                    self._normalize_document_asset(document, scope="project", default_title=f"{DEFAULT_PROJECT_DOCUMENT_TITLE} {index}")
                    for index, document in enumerate(project.get("documents", []), start=1)
                    if isinstance(document, dict) and _content_text(document.get("content")).strip()
                ]
                if normalized_documents != project.get("documents", []):
                    project["documents"] = normalized_documents
                    changed = True
                normalized_code_files = [
                    self._normalize_code_file(code_file)
                    for code_file in project.get("code_files", [])
                    if isinstance(code_file, dict) and _content_text(code_file.get("content")).strip()
                ]
                if normalized_code_files != project.get("code_files", []):
                    project["code_files"] = normalized_code_files
                    changed = True
        if changed:
            for workspace in self._workspaces.values():
                self.repository.save_workspace(workspace)
