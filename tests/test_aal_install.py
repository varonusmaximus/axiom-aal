# @!testing

"""Tests for aal install --hooks."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aal.install import InstallOptions, cmd_install, cmd_upgrade

_CURSOR_DIR = "_aal_cursor"


@pytest.fixture(autouse=True)
def _aal_cursor_dir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AAL_CURSOR_DIR", _CURSOR_DIR)


def _cursor(root: Path) -> Path:
    return root / os.environ.get("AAL_CURSOR_DIR", _CURSOR_DIR)


def test_install_hooks_dry_run(tmp_path: Path):
    root = tmp_path
    code = cmd_install(
        InstallOptions(root=root, project=True, hooks=True, ci=True, dry_run=True),
    )
    assert code == 0
    assert not (_cursor(root) / "domains.yaml").exists()
    assert not (_cursor(root) / "hooks.json").exists()


def test_install_hooks_writes_template_files(tmp_path: Path):
    root = tmp_path
    code = cmd_install(
        InstallOptions(root=root, project=True, hooks=True, ci=False, dry_run=False),
    )
    assert code == 0
    assert not (_cursor(root) / "domains.yaml").exists()
    assert not (_cursor(root) / "bootstrap.yaml").exists()
    assert (_cursor(root) / "aal.yaml").is_file()
    assert (_cursor(root) / "hooks/aal-inject.sh").is_file()
    hooks_json = (_cursor(root) / "hooks.json").read_text(encoding="utf-8")
    assert "matcher" in hooks_json
    assert "Write|StrReplace" in hooks_json
    assert "failClosed" in hooks_json
    assert (_cursor(root) / ".aal-manifest.json").is_file()


def test_upgrade_requires_manifest(tmp_path: Path, capsys):
    root = tmp_path
    assert cmd_upgrade(root) == 1
    assert "missing" in capsys.readouterr().out.lower()
