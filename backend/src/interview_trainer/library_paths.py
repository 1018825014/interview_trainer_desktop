from __future__ import annotations

from pathlib import Path


def resolve_library_root(storage_root: Path | str | None = None) -> Path:
    if storage_root is not None:
        root = Path(storage_root).expanduser().resolve()
    else:
        root = Path(__file__).resolve().parents[2] / "data" / "library"
    root.mkdir(parents=True, exist_ok=True)
    (root / "objects").mkdir(parents=True, exist_ok=True)
    return root
