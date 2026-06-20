from __future__ import annotations

import os
import shutil
from pathlib import Path

from aal import __version__
from aal.bundle import list_bundled_domains
from aal.config import cursor_config_dir, load_config
from aal.constants import BOOTSTRAP_FILE, DOMAINS_FILE, LEGACY_MANIFEST_FILE, MANIFEST_FILE


def _check_cursor_hooks(root: Path, cursor_dir: Path, *, strict: bool) -> int:
    """Verify inject hook files and smoke-test the Python adapter."""
    issues = 0
    hooks_json = cursor_dir / "hooks.json"
    hook_script = cursor_dir / "hooks" / "aal-inject.sh"

    if not hooks_json.is_file():
        print("MISSING: .cursor/hooks.json — run: aal install --project --hooks")
        return 1

    print("OK: .cursor/hooks.json")
    hooks_text = hooks_json.read_text(encoding="utf-8")
    if "aal-inject.sh" not in hooks_text:
        print("MISSING: hooks.json must reference aal-inject.sh")
        issues += 1
    elif strict:
        print("OK: hooks.json references aal-inject.sh")

    if "matcher" not in hooks_text:
        print("WARN: hooks.json lacks matcher (stale install) — run install --hooks --force")
        if strict:
            issues += 1
    else:
        print("OK: hooks.json has matcher")

    if not hook_script.is_file():
        print("MISSING: .cursor/hooks/aal-inject.sh")
        issues += 1
    elif not os.access(hook_script, os.X_OK):
        print("MISSING: .cursor/hooks/aal-inject.sh is not executable")
        issues += 1
    else:
        print("OK: .cursor/hooks/aal-inject.sh (executable)")

    smoke_file: Path | None = None
    for candidate in root.rglob("*.py"):
        if any(part.startswith(".") for part in candidate.relative_to(root).parts):
            continue
        try:
            head = candidate.read_text(encoding="utf-8", errors="replace")[:500]
        except OSError:
            continue
        if "@!" in head:
            smoke_file = candidate
            break
    if smoke_file is None:
        smoke_file = Path(__file__).resolve().parent / "cursor_hook.py"
    if not smoke_file.is_file():
        print("OPTIONAL: hook smoke test skipped (no annotated file found)")
        return issues

    from aal.cursor_hook import run_cursor_pretooluse

    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(smoke_file.resolve())},
        "workspace_roots": [str(root.resolve())],
    }
    try:
        result = run_cursor_pretooluse(root, payload)
        if result.get("permission") not in ("allow", "deny"):
            print("MISSING: hook smoke test returned invalid permission JSON")
            issues += 1
        else:
            print(f"OK: hook smoke test (permission={result['permission']})")
    except Exception as exc:
        print(f"MISSING: hook smoke test failed: {exc}")
        issues += 1

    return issues


def cmd_doctor(root: Path, *, strict: bool = False) -> int:
    issues = 0
    print(f"[AAL] Doctor v{__version__} — {root}")
    print()

    cli = shutil.which("aal")
    if cli:
        print(f"OK: `aal` CLI available ({cli})")
    else:
        try:
            import aal  # noqa: F401

            print("OK: `aal` importable (use `python -m aal.cli`)")
        except ImportError:
            print("MISSING: pip install axiom-aal")
            issues += 1

    cursor_dir = cursor_config_dir(root)
    if not cursor_dir.is_dir():
        print("MISSING: .cursor/ — run: aal install --project --hooks")
        issues += 1
    else:
        print("OK: .cursor/ present")
        for name in ("aal.yaml", DOMAINS_FILE, BOOTSTRAP_FILE):
            path = cursor_dir / name
            if path.is_file():
                print(f"OK: {path.relative_to(root)}")
            elif name == BOOTSTRAP_FILE and not strict:
                print(f"OPTIONAL: {path.relative_to(root)}")
            else:
                print(f"MISSING: {path.relative_to(root)}")
                issues += 1

        manifest_path = cursor_dir / MANIFEST_FILE
        legacy_manifest = cursor_dir / LEGACY_MANIFEST_FILE
        if manifest_path.is_file():
            print(f"OK: {manifest_path.relative_to(root)}")
        elif legacy_manifest.is_file():
            print(f"OK: {legacy_manifest.relative_to(root)} (legacy manifest)")
        elif not strict:
            print(f"OPTIONAL: {manifest_path.relative_to(root)}")
        else:
            print(f"MISSING: {manifest_path.relative_to(root)}")
            issues += 1

        skills_dir = cursor_dir / "skills"
        if skills_dir.is_dir() and any(
            (skills_dir / d / "SKILL.md").exists() for d in skills_dir.iterdir() if d.is_dir()
        ):
            count = sum(
                1 for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()
            )
            print(f"OK: .cursor/skills/ ({count} SKILL.md tree(s))")
        else:
            print(
                "MISSING: .cursor/skills/*/SKILL.md — sync skills in consumer repo (e.g. axiompy-skills --project)"
            )
            issues += 1

        issues += _check_cursor_hooks(root, cursor_dir, strict=strict)

    cursor_rule = cursor_dir / "rules" / "aal.mdc"
    if cursor_rule.is_file():
        print("OK: .cursor/rules/aal.mdc")
    else:
        print("OPTIONAL: .cursor/rules/aal.mdc — run: aal install --project --hooks")

    ci_workflow = root / ".github/workflows/aal-gate.yml"
    if ci_workflow.is_file():
        print("OK: .github/workflows/aal-gate.yml")
    else:
        print("OPTIONAL: CI workflow — run: aal install --project --hooks")

    config = load_config(root)
    print(f"OK: scan_entire_file={config.get('scan_entire_file', True)}")

    bundled = list_bundled_domains()
    if bundled:
        print(f"INFO: bundled domain templates: {', '.join(bundled)}")
    else:
        print("INFO: domain registry is consumer-owned (.cursor/domains.yaml)")

    print()
    if issues:
        print(f"[AAL] Doctor found {issues} issue(s).")
        return 1
    print("[AAL] Doctor: all required components present.")
    return 0
