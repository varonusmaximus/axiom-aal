"""Cursor preToolUse hook adapter — parse stdin, resolve domains, emit inject JSON."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from aal.inject_log import append_inject_log, default_inject_log_path
from aal.middleware import EditIntent
from aal.resolve import resolve_edit

logger = logging.getLogger(__name__)

_EDIT_TOOLS = frozenset({"Write", "StrReplace", "Edit"})


def _path_from_tool_input(tool_input: dict[str, Any]) -> str | None:
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if value:
            return str(value)
    return None


def normalize_file_path(
    raw: str,
    root: Path,
    *,
    workspace_roots: list[str] | None = None,
    cwd: str | None = None,
) -> str:
    """Return repo-relative path when possible."""
    path = Path(raw)
    if not path.is_absolute():
        return raw.lstrip("./")

    resolved = path.resolve()
    candidates = [root.resolve()]
    if workspace_roots:
        candidates = [Path(w).resolve() for w in workspace_roots] + candidates
    if cwd:
        candidates.insert(0, Path(cwd).resolve())

    for base in candidates:
        try:
            return str(resolved.relative_to(base))
        except ValueError:
            continue
    return raw


def infer_target_line(
    root: Path,
    rel_file: str,
    tool_input: dict[str, Any],
) -> int:
    """Infer annotation line from StrReplace old_string or file length."""
    from aal.config import load_config
    from aal.scanner import read_file_for_parse

    path = root / rel_file
    old_string = tool_input.get("old_string") or ""
    if old_string and path.is_file():
        _, content = read_file_for_parse(path, load_config(root))
        first_line = old_string.splitlines()[0] if old_string else ""
        if first_line:
            for line_no, line in enumerate(content.splitlines(), 1):
                if first_line in line:
                    return line_no

    if path.is_file():
        _, content = read_file_for_parse(path, load_config(root))
        return len(content.splitlines()) or 1
    return 1


def parse_cursor_pretooluse(
    payload: dict[str, Any],
    root: Path,
    *,
    file_override: str | None = None,
    line_override: int | None = None,
) -> EditIntent | None:
    """Map Cursor preToolUse stdin to EditIntent, or None if not a file edit."""
    if file_override:
        return EditIntent(
            file_path=normalize_file_path(file_override, root),
            target_line=line_override or 1,
        )

    tool_name = payload.get("tool_name") or ""
    if tool_name not in _EDIT_TOOLS:
        return None

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    raw_path = _path_from_tool_input(tool_input)
    if not raw_path:
        return None

    workspace_roots = payload.get("workspace_roots") or []
    if not isinstance(workspace_roots, list):
        workspace_roots = []

    rel_file = normalize_file_path(
        raw_path,
        root,
        workspace_roots=[str(w) for w in workspace_roots],
        cwd=payload.get("cwd"),
    )
    line = line_override or infer_target_line(root, rel_file, tool_input)
    return EditIntent(file_path=rel_file, target_line=line)


def _format_agent_message(payload: dict[str, Any]) -> str:
    domains = ", ".join(payload.get("domains") or []) or "(none)"
    header = f"# AAL inject: {payload['file']}:{payload['line']}\ndomains: {domains}\n\n"
    content = payload.get("content") or ""
    return header + content if content else header.rstrip()


def run_cursor_pretooluse(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve domains for a Cursor preToolUse event; return permission JSON."""
    log_path = default_inject_log_path(root)
    file_override = os.environ.get("FILE") or os.environ.get("CURSOR_FILE_PATH")
    line_override: int | None = None
    if os.environ.get("LINE") or os.environ.get("CURSOR_LINE"):
        line_override = int(os.environ.get("LINE") or os.environ.get("CURSOR_LINE") or "1")

    intent = parse_cursor_pretooluse(
        payload,
        root,
        file_override=file_override or None,
        line_override=line_override,
    )
    if intent is None:
        return {"permission": "allow"}

    rel_file = intent.file_path
    line = intent.target_line or 1

    try:
        resolve_payload = resolve_edit(root, rel_file, target_line=line)
    except (FileNotFoundError, ValueError) as exc:
        append_inject_log(
            log_path,
            file=rel_file,
            line=line,
            ok=False,
            error=str(exc),
        )
        msg = (
            f"AAL inject failed for {rel_file}:{line}: {exc}\nFix with: aal verify-domains --strict"
        )
        logger.warning(msg)
        return {
            "permission": "deny",
            "user_message": f"AAL inject blocked edit: {exc}",
            "agent_message": msg,
        }

    append_inject_log(
        log_path,
        file=resolve_payload["file"],
        line=resolve_payload["line"],
        ok=True,
        payload=resolve_payload,
    )

    if not resolve_payload.get("domains"):
        return {"permission": "allow"}

    return {
        "permission": "allow",
        "agent_message": _format_agent_message(resolve_payload),
    }


def cmd_cursor_pretooluse(root: Path, *, stdin_text: str | None = None) -> int:
    """Read hook stdin, write permission JSON to stdout."""
    raw = stdin_text if stdin_text is not None else sys.stdin.read()
    payload: dict[str, Any] = {}
    if raw.strip():
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("Invalid hook stdin JSON: %s", exc)
            print(
                json.dumps(
                    {
                        "permission": "deny",
                        "user_message": "AAL hook received invalid JSON",
                        "agent_message": f"AAL hook stdin parse error: {exc}",
                    }
                )
            )
            return 0

    result = run_cursor_pretooluse(root, payload)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry for Cursor preToolUse hook."""
    _ = argv
    return cmd_cursor_pretooluse(Path.cwd().resolve())


if __name__ == "__main__":
    sys.exit(main())
