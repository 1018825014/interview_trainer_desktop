from __future__ import annotations

import time
from pathlib import Path, PurePosixPath
from uuid import uuid4
from typing import Any

from .knowledge import KnowledgeCompiler
from .library_repository import LibraryRepository


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
        self._workspaces: dict[str, dict[str, Any]] = self.repository.load_workspaces()

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

        projects = workspace["knowledge"].setdefault("projects", [])
        project = next((item for item in projects if _clean_text(item.get("name")) == project_name), None)
        if project is None:
            project = self._default_project(project_name)
            projects.append(project)

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

    def _serialize(self, workspace: dict[str, Any]) -> dict[str, Any]:
        return {
            "workspace_id": workspace["workspace_id"],
            "name": workspace["name"],
            "knowledge": workspace["knowledge"],
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
        project["business_value"] = _clean_text(payload.get("business_value")) or project["business_value"]
        project["architecture"] = _clean_text(payload.get("architecture")) or project["architecture"]
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
            "name": name,
            "business_value": "",
            "architecture": "",
            "repo_summaries": [],
            "documents": [],
            "code_files": [],
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
