"""Append inject resolve records to a reviewable JSONL log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_inject_log_path(root: Path) -> Path:
    from aal.config import load_config

    config = load_config(root)
    rel = config.get("inject_log", ".cursor/logs/aal-inject.jsonl")
    path = Path(rel)
    return path if path.is_absolute() else root / path


def append_inject_log(
    log_path: Path,
    *,
    file: str,
    line: int,
    ok: bool,
    payload: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Append one JSONL record for an inject attempt."""
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "file": file,
        "line": line,
        "ok": ok,
    }
    if ok and payload is not None:
        entry["domains"] = payload.get("domains", [])
        entry["skill_paths"] = [s.get("path") for s in payload.get("skills", [])]
        entry["content_chars"] = len(payload.get("content", ""))
        entry["resolve"] = payload
    if error:
        entry["error"] = error

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
