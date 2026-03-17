from __future__ import annotations

import time
from pathlib import Path, PurePosixPath
from uuid import uuid4
from typing import Any

from .knowledge import KnowledgeCompiler
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


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


class WorkspaceManager:
    def __init__(
        self,
        compiler: KnowledgeCompiler | None = None,
        storage_root: Path | str | None = None,
    ) -> None:
        self.compiler = compiler or KnowledgeCompiler()
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
        }
        self._workspaces[workspace_id] = workspace
        self.repository.save_workspace(workspace)
        return self._serialize(workspace)

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
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
        workspace["compiled_knowledge"] = None
        workspace["compile_summary"] = None
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
        if "documents" in payload:
            project["documents"] = [
                {
                    "path": _clean_text(item.get("path")),
                    "content": _clean_text(item.get("content")),
                }
                for item in payload.get("documents", [])
                if isinstance(item, dict) and _clean_text(item.get("content"))
            ]
        if "code_files" in payload:
            project["code_files"] = [
                {
                    "path": _clean_text(item.get("path")) or "src/main.py",
                    "content": _clean_text(item.get("content")),
                }
                for item in payload.get("code_files", [])
                if isinstance(item, dict) and _clean_text(item.get("content"))
            ]
        workspace["compiled_knowledge"] = None
        workspace["compile_summary"] = None
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize_project(project)

    def delete_project(self, project_id: str) -> dict[str, str]:
        workspace, project = self._find_project(project_id)
        projects = workspace["knowledge"].get("projects", [])
        workspace["knowledge"]["projects"] = [item for item in projects if item is not project]
        workspace["compiled_knowledge"] = None
        workspace["compile_summary"] = None
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return {"status": "deleted", "project_id": project_id}

    def list_project_repos(self, project_id: str) -> dict[str, Any]:
        _, project = self._find_project(project_id)
        return {"repos": [dict(item) for item in project.get("repo_summaries", [])]}

    def import_project_repo(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace, project = self._find_project(project_id)
        return self._import_into_project(workspace, project, payload)

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
        return {"bundles": [dict(item) for item in workspace.get("compiled_bundles", [])]}

    def get_bundle(self, bundle_id: str) -> dict[str, Any]:
        for workspace in self._workspaces.values():
            for bundle in workspace.get("compiled_bundles", []):
                if _clean_text(bundle.get("bundle_id")) == bundle_id:
                    return dict(bundle)
        raise KeyError(bundle_id)

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
        workspace.setdefault("compiled_bundles", []).append(dict(payload["activation_summary"]))
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return payload

    def update_workspace(self, workspace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        if "name" in payload:
            workspace["name"] = _clean_text(payload.get("name")) or workspace["name"]
        if "knowledge" in payload:
            workspace["knowledge"] = self._normalize_knowledge_payload(payload.get("knowledge", {}))
            workspace["compiled_knowledge"] = None
            workspace["compile_summary"] = None
        workspace["updated_at"] = time.time()
        self.repository.save_workspace(workspace)
        return self._serialize(workspace)

    def compile_workspace(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._workspaces[workspace_id]
        compiled = self.compiler.compile(workspace["knowledge"])
        workspace["compiled_knowledge"] = self.compiler.to_dict(compiled)
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
            "knowledge": workspace["knowledge"],
            "overlays": [self._serialize_overlay(item) for item in workspace.get("overlays", [])],
            "presets": [self._serialize_preset(item) for item in workspace.get("presets", [])],
            "compiled_bundles": [dict(item) for item in workspace.get("compiled_bundles", [])],
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
                {
                    "title": _clean_text(document.get("title")) or f"Role Document {index}",
                    "content": _clean_text(document.get("content")),
                }
                for index, document in enumerate(role_documents_input, start=1)
                if isinstance(document, dict) and _clean_text(document.get("content"))
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
            {
                "path": _clean_text(item.get("path")),
                "content": _clean_text(item.get("content")),
            }
            for item in payload.get("documents", [])
            if isinstance(item, dict) and _clean_text(item.get("content"))
        ]
        project["code_files"] = [
            {
                "path": _clean_text(item.get("path")) or "src/main.py",
                "content": _clean_text(item.get("content")),
            }
            for item in payload.get("code_files", [])
            if isinstance(item, dict) and _clean_text(item.get("content"))
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
            "repo_summaries": [dict(item) for item in project.get("repo_summaries", [])],
            "documents": [dict(item) for item in project.get("documents", [])],
            "code_files": [dict(item) for item in project.get("code_files", [])],
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
        max_files = max(1, int(payload.get("max_files", 80)))
        max_chars = max(200, int(payload.get("max_chars_per_file", 12000)))
        docs: list[dict[str, Any]] = []
        code_files: list[dict[str, Any]] = []

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
                text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            except OSError:
                continue
            if not text:
                continue
            relative_path = self._relative_path(root, file_path)
            if len(text) > max_chars:
                text = text[:max_chars] + "\n... [truncated]"
            if suffix in DOC_EXTENSIONS:
                docs.append({"path": relative_path, "content": text})
            else:
                code_files.append({"path": relative_path, "content": text})

        project["name"] = project_name or project.get("name", "")
        project["documents"] = docs or project.get("documents", [])
        project["code_files"] = code_files or project.get("code_files", [])
        if "business_value" in payload:
            project["business_value"] = _clean_text(payload.get("business_value")) or project.get("business_value", "")
        if "architecture" in payload:
            project["architecture"] = _clean_text(payload.get("architecture")) or project.get("architecture", "")

        workspace["compiled_knowledge"] = None
        workspace["compile_summary"] = None
        workspace["updated_at"] = time.time()
        repo_summaries = project.setdefault("repo_summaries", [])
        existing_repo = next(
            (
                item
                for item in repo_summaries
                if _clean_text(item.get("root_path")) == str(root)
            ),
            None,
        )
        repo_summary = {
            "repo_id": _clean_text(existing_repo.get("repo_id")) if isinstance(existing_repo, dict) else str(uuid4()),
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
                ):
                    if field not in project:
                        project[field] = [] if field.endswith("s") or field in {"key_metrics", "tradeoffs"} else ""
                        changed = True
                if not isinstance(project.get("key_metrics"), list):
                    project["key_metrics"] = self._normalize_lines(project.get("key_metrics"))
                    changed = True
                for field in ("tradeoffs", "failure_cases", "limitations", "upgrade_plan", "interviewer_hooks"):
                    if not isinstance(project.get(field), list):
                        project[field] = self._normalize_lines(project.get(field))
                        changed = True
                if "repo_summaries" not in project:
                    project["repo_summaries"] = []
                    changed = True
        if changed:
            for workspace in self._workspaces.values():
                self.repository.save_workspace(workspace)
