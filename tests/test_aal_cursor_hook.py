# @!testing

"""Tests for Cursor preToolUse hook adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aal.cursor_hook import (
    cmd_cursor_pretooluse,
    infer_target_line,
    normalize_file_path,
    parse_cursor_pretooluse,
    run_cursor_pretooluse,
)
from aal.inject_log import default_inject_log_path
from tests.aal_helpers import setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AAL_CURSOR_DIR", _CURSOR_DIR)


def test_normalize_file_path_relative():
    root = Path("/repo")
    assert normalize_file_path("app.py", root) == "app.py"


def test_normalize_file_path_absolute_under_root():
    root = Path("/repo")
    assert normalize_file_path("/repo/pkg/mod.py", root, workspace_roots=["/repo"]) == "pkg/mod.py"


def test_parse_cursor_pretooluse_ignores_shell():
    root = Path("/repo")
    assert parse_cursor_pretooluse({"tool_name": "Shell", "tool_input": {}}, root) is None


def test_parse_cursor_pretooluse_write(tmp_path: Path):
    root = tmp_path
    target = root / "app.py"
    target.write_text("# @!testing\n", encoding="utf-8")
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target)},
        "workspace_roots": [str(root)],
    }
    intent = parse_cursor_pretooluse(payload, root)
    assert intent is not None
    assert intent.file_path == "app.py"
    assert intent.target_line == 1


def test_infer_target_line_from_strreplace(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    app = root / "app.py"
    app.write_text("# @!testing\n\ndef foo():\n    pass\n", encoding="utf-8")
    line = infer_target_line(
        root,
        "app.py",
        {"old_string": "def foo():"},
    )
    assert line == 3


def test_run_cursor_pretooluse_allow_with_content(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "app.py").write_text("# @!testing\n", encoding="utf-8")
    log_path = default_inject_log_path(root)

    result = run_cursor_pretooluse(
        root,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(root / "app.py")},
            "workspace_roots": [str(root)],
        },
    )
    assert result["permission"] == "allow"
    assert "agent_message" in result
    assert "testing" in result["agent_message"]
    assert log_path.is_file()
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["ok"] is True
    assert entry["domains"] == ["testing"]


def test_run_cursor_pretooluse_deny_unknown_domain(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "bad.py").write_text("# @!missing\n", encoding="utf-8")

    result = run_cursor_pretooluse(
        root,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(root / "bad.py")},
            "workspace_roots": [str(root)],
        },
    )
    assert result["permission"] == "deny"
    assert "verify-domains" in result["agent_message"]


def test_run_cursor_pretooluse_allow_unannotated(tmp_path: Path):
    root = tmp_path
    setup_minimal_repo(root)
    (root / "plain.py").write_text("x = 1\n", encoding="utf-8")

    result = run_cursor_pretooluse(
        root,
        {
            "tool_name": "Write",
            "tool_input": {"file_path": str(root / "plain.py")},
            "workspace_roots": [str(root)],
        },
    )
    assert result["permission"] == "allow"
    assert "agent_message" not in result


def test_cmd_cursor_pretooluse_invalid_json(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root)
    assert cmd_cursor_pretooluse(root, stdin_text="{not json") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "deny"


def test_cmd_cursor_pretooluse_strreplace_path_key(tmp_path: Path, capsys):
    root = tmp_path
    setup_minimal_repo(root)
    app = root / "app.py"
    app.write_text("# @!testing\n\ndef bar():\n    return 1\n", encoding="utf-8")
    stdin = json.dumps(
        {
            "tool_name": "StrReplace",
            "tool_input": {
                "path": str(app),
                "old_string": "def bar():",
                "new_string": "def bar():\n    pass",
            },
            "workspace_roots": [str(root)],
        }
    )
    assert cmd_cursor_pretooluse(root, stdin_text=stdin) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["permission"] == "allow"
    assert "agent_message" in out
