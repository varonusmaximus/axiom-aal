# @!testing

"""Tests for AAL inject JSONL logging."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aal.inject_log import append_inject_log, default_inject_log_path
from aal.resolve import cmd_resolve
from tests.aal_helpers import setup_minimal_repo

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AAL_CURSOR_DIR", _CURSOR_DIR)


def test_append_inject_log_writes_jsonl(tmp_path: Path):
    log_path = tmp_path / "logs" / "inject.jsonl"
    append_inject_log(
        log_path,
        file="app.py",
        line=3,
        ok=True,
        payload={
            "domains": ["testing"],
            "skills": [{"path": ".cursor/skills/testing/SKILL.md"}],
            "content": "hello",
        },
    )
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["ok"] is True
    assert entry["file"] == "app.py"
    assert entry["domains"] == ["testing"]
    assert entry["content_chars"] == 5
    assert "resolve" in entry


def test_default_inject_log_path_from_config(tmp_path: Path):
    root = tmp_path
    cursor = root / _CURSOR_DIR
    cursor.mkdir(parents=True)
    (cursor / "aal.yaml").write_text("inject_log: custom/inject.jsonl\n", encoding="utf-8")
    assert default_inject_log_path(root) == root / "custom" / "inject.jsonl"


def test_cmd_resolve_with_log(tmp_path: Path, capsys):
    root = tmp_path
    log_path = root / "inject.jsonl"
    setup_minimal_repo(root)
    (root / "app.py").write_text("# @!testing\n", encoding="utf-8")

    assert cmd_resolve(root, "app.py", as_json=False, log_path=log_path) == 0
    out = capsys.readouterr().out
    assert "log: inject.jsonl" in out
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["ok"] is True
    assert entry["domains"] == ["testing"]


def test_cmd_resolve_logs_failure(tmp_path: Path):
    root = tmp_path
    log_path = root / "inject.jsonl"
    setup_minimal_repo(root)
    (root / "bad.py").write_text("# @!missing\n", encoding="utf-8")

    assert cmd_resolve(root, "bad.py", log_path=log_path) == 1
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["ok"] is False
    assert "unknown domain" in entry["error"]
