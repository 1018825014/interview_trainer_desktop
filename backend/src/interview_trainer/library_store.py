from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .library_paths import resolve_library_root


class LibraryStore:
    def __init__(self, storage_root: Path | str | None = None) -> None:
        self.root = resolve_library_root(storage_root)
        self.db_path = self.root / "library.db"
        self.objects_root = self.root / "objects"
        self._initialize()

    def load_workspaces(self) -> dict[str, dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT workspace_id, payload_json
                FROM workspaces
                """
            ).fetchall()
        workspaces: dict[str, dict[str, Any]] = {}
        for row in rows:
            workspaces[str(row["workspace_id"])] = json.loads(str(row["payload_json"]))
        return workspaces

    def save_workspace(self, workspace: dict[str, Any]) -> None:
        payload_json = json.dumps(workspace, ensure_ascii=False)
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO workspaces (
                    workspace_id,
                    name,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id) DO UPDATE SET
                    name = excluded.name,
                    payload_json = excluded.payload_json,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                (
                    str(workspace["workspace_id"]),
                    str(workspace["name"]),
                    payload_json,
                    float(workspace["created_at"]),
                    float(workspace["updated_at"]),
                ),
            )
            connection.commit()

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            connection.commit()
