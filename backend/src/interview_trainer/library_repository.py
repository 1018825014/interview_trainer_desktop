from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from uuid import uuid4
from typing import Any

from .library_store import LibraryStore


class LibraryRepository:
    def __init__(self, storage_root: Path | str | None = None) -> None:
        self.store = LibraryStore(storage_root=storage_root)
        self.objects_root = self.store.objects_root

    def load_workspaces(self) -> dict[str, dict[str, Any]]:
        stored = self.store.load_workspaces()
        return {
            workspace_id: self._hydrate_workspace(workspace)
            for workspace_id, workspace in stored.items()
        }

    def save_workspace(self, workspace: dict[str, Any]) -> None:
        dehydrated = self._dehydrate_workspace(workspace)
        self.store.save_workspace(dehydrated)

    def _hydrate_workspace(self, workspace: dict[str, Any]) -> dict[str, Any]:
        hydrated = copy.deepcopy(workspace)
        knowledge = hydrated.get("knowledge", {})
        for project in knowledge.get("projects", []):
            for document in project.get("documents", []):
                self._hydrate_text_item(document)
            for code_file in project.get("code_files", []):
                self._hydrate_text_item(code_file)
            project.setdefault("repo_summaries", [])
        for document in knowledge.get("role_documents", []):
            self._hydrate_text_item(document)
        return hydrated

    def _dehydrate_workspace(self, workspace: dict[str, Any]) -> dict[str, Any]:
        dehydrated = copy.deepcopy(workspace)
        knowledge = dehydrated.get("knowledge", {})
        workspace_root = self.objects_root / str(dehydrated["workspace_id"])
        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        for project in knowledge.get("projects", []):
            for document in project.get("documents", []):
                self._dehydrate_text_item(workspace_root, "documents", document)
            for code_file in project.get("code_files", []):
                self._dehydrate_text_item(workspace_root, "code_files", code_file)
            project.setdefault("repo_summaries", [])
        for document in knowledge.get("role_documents", []):
            self._dehydrate_text_item(workspace_root, "role_documents", document)
        return dehydrated

    def _hydrate_text_item(self, item: dict[str, Any]) -> None:
        object_path = str(item.get("object_path", "")).strip()
        if not object_path:
            return
        content_path = self.objects_root / object_path
        if not content_path.exists():
            item["content"] = ""
            return
        item["content"] = content_path.read_text(encoding="utf-8")

    def _dehydrate_text_item(self, workspace_root: Path, folder: str, item: dict[str, Any]) -> None:
        content = str(item.get("content", ""))
        target_dir = workspace_root / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        object_name = f"{uuid4()}.txt"
        object_path = target_dir / object_name
        object_path.write_text(content, encoding="utf-8")
        item["object_path"] = object_path.relative_to(self.objects_root).as_posix()
        item.pop("content", None)

    def debug_dump(self) -> str:
        return json.dumps(self.store.load_workspaces(), ensure_ascii=False, indent=2)
