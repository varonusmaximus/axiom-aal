"""Install AAL templates into a consumer repository."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from aal import __version__
from aal.bundle import bundled_file, load_manifest
from aal.constants import LEGACY_MANIFEST_FILE, MANIFEST_FILE, cursor_config_dir_name


@dataclass
class InstallOptions:
    root: Path
    project: bool = True
    hooks: bool = False
    ci: bool = True
    force: bool = False
    dry_run: bool = False


def _copy_template(src: Path, dest: Path, opts: InstallOptions) -> bool:
    if dest.exists() and not opts.force:
        print(f"  skip (exists): {dest.relative_to(opts.root)}")
        return False
    if opts.dry_run:
        print(f"  would write: {dest.relative_to(opts.root)}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    if dest.suffix == ".sh":
        dest.chmod(dest.stat().st_mode | 0o111)
    print(f"  wrote: {dest.relative_to(opts.root)}")
    return True


def _manifest_path(cursor_dir: Path) -> Path:
    primary = cursor_dir / MANIFEST_FILE
    legacy = cursor_dir / LEGACY_MANIFEST_FILE
    return primary if primary.is_file() else legacy


def cmd_install(opts: InstallOptions) -> int:
    manifest = load_manifest()
    cursor_dir = opts.root / cursor_config_dir_name()

    print(f"[AAL] Installing into {opts.root}")

    _copy_template(bundled_file("aal.yaml"), cursor_dir / "aal.yaml", opts)

    if opts.hooks:
        print("[AAL] Cursor hooks:")
        _copy_template(bundled_file("cursor/hooks.json"), cursor_dir / "hooks.json", opts)
        _copy_template(
            bundled_file("cursor/hooks/aal-inject.sh"),
            cursor_dir / "hooks" / "aal-inject.sh",
            opts,
        )
        _copy_template(
            bundled_file("cursor/rules/aal.mdc"),
            cursor_dir / "rules" / "aal.mdc",
            opts,
        )

    if opts.ci:
        print("[AAL] CI:")
        _copy_template(
            bundled_file("github/workflows/aal-gate.yml"),
            opts.root / ".github" / "workflows" / "aal-gate.yml",
            opts,
        )

    managed = manifest.get("managed_paths", [])
    manifest_doc = {
        "version": manifest.get("version", "1.0"),
        "aal_version": __version__,
        "managed_paths": managed,
    }
    manifest_path = cursor_dir / MANIFEST_FILE
    if opts.dry_run:
        print(f"  would write: {manifest_path.relative_to(opts.root)}")
    else:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest_doc, indent=2) + "\n", encoding="utf-8")
        print(f"  wrote: {manifest_path.relative_to(opts.root)}")

    if opts.dry_run:
        print("\n[AAL] Dry run complete. Re-run without --dry-run to apply.")
        return 0

    print("\n[AAL] Installation complete.")
    print("\nNext steps:")
    print("  1. Commit consumer-owned .cursor/domains.yaml and .cursor/bootstrap.yaml")
    print("  2. Sync domain skills (e.g. axiompy-skills --project in axiompy)")
    print("  3. aal bootstrap suggest")
    print("  4. aal verify-domains --strict")
    return 0


def cmd_upgrade(root: Path, *, force: bool = False, dry_run: bool = False) -> int:
    cursor_dir = root / cursor_config_dir_name()
    manifest_path = _manifest_path(cursor_dir)
    if not manifest_path.is_file():
        print(
            "ERROR: missing .cursor/.aal-manifest.json — run: aal install --project --hooks"
        )
        return 1

    opts = InstallOptions(root=root, hooks=True, ci=True, force=force, dry_run=dry_run)
    return cmd_install(opts)
