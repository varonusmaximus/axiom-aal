"""AAL command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from aal import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aal",
        description="Agent Annotation Language — domain resolve, inject, verify, and install.",
    )
    parser.add_argument("--version", action="store_true", help="Print aal version and exit.")

    sub = parser.add_subparsers(dest="command")

    install = sub.add_parser("install", help="Install AAL hooks, config, and CI templates")
    install.add_argument("--project", action="store_true", help="Install under <cwd>/.cursor/")
    install.add_argument("--hooks", action="store_true", help="Install hooks and aal.mdc rule")
    install.add_argument("--no-ci", action="store_true", help="Skip CI workflow template")
    install.add_argument("--force", action="store_true", help="Overwrite existing config files")
    install.add_argument("--dry-run", action="store_true")

    upgrade = sub.add_parser(
        "upgrade", help="Re-apply manifest-managed paths after package upgrade"
    )
    upgrade.add_argument("--force", action="store_true")
    upgrade.add_argument("--dry-run", action="store_true")

    verify = sub.add_parser("verify-domains", help="Verify @!domain annotations resolve to skills")
    verify.add_argument("--strict", action="store_true")
    verify.add_argument("--files", nargs="+", default=None, help="Only check these paths")

    resolve = sub.add_parser("resolve", help="Resolve domains and skill content for inject")
    resolve.add_argument("--file", required=True)
    resolve.add_argument("--line", type=int, default=None)
    resolve.add_argument("--json", action="store_true")
    resolve.add_argument(
        "--log",
        nargs="?",
        const="default",
        default=None,
        metavar="PATH",
        help="Append JSONL inject record (default: inject_log from .cursor/aal.yaml)",
    )

    bootstrap = sub.add_parser("bootstrap", help="Bootstrap file-level annotations")
    boot_sub = bootstrap.add_subparsers(dest="bootstrap_cmd", required=True)
    boot_sub.add_parser("suggest", help="Suggest domains for unannotated P0 files")
    apply_p = boot_sub.add_parser("apply", help="Apply file-level annotations")
    apply_p.add_argument("--level", choices=["file"], default="file")
    apply_p.add_argument(
        "--apply", action="store_true", help="Write annotations (default: dry-run)"
    )
    migrate_p = boot_sub.add_parser(
        "migrate", help="Replace existing file-level annotations from path hints"
    )
    migrate_p.add_argument(
        "--apply", action="store_true", help="Write annotations (default: dry-run)"
    )

    annotate = sub.add_parser("annotate", help="Add file-level @!domain to an existing file")
    annotate.add_argument("file")
    annotate.add_argument("--domain", required=True)
    annotate.add_argument("--dry-run", action="store_true")

    doctor = sub.add_parser("doctor", help="Verify AAL installation health")
    doctor.add_argument("--strict", action="store_true")

    hook = sub.add_parser("hook", help="Cursor hook adapters")
    hook_sub = hook.add_subparsers(dest="hook_cmd", required=True)
    hook_sub.add_parser(
        "cursor-pretooluse",
        help="preToolUse adapter: read stdin JSON, resolve domains, write permission JSON",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    cwd = Path.cwd()

    if args.version:
        print(f"aal {__version__}")
        return 0

    if args.command is None:
        parser.print_help()
        return 2

    root = cwd.resolve()

    if args.command == "install":
        from aal.install import InstallOptions, cmd_install

        opts = InstallOptions(
            root=root,
            project=args.project,
            hooks=args.hooks,
            ci=not args.no_ci,
            force=args.force,
            dry_run=args.dry_run,
        )
        return cmd_install(opts)

    if args.command == "upgrade":
        from aal.install import cmd_upgrade

        return cmd_upgrade(root, force=args.force, dry_run=args.dry_run)

    if args.command == "verify-domains":
        from aal.verify import cmd_verify_domains

        return cmd_verify_domains(root, args.strict, files=args.files)

    if args.command == "resolve":
        from aal.inject_log import default_inject_log_path
        from aal.resolve import cmd_resolve

        log_path = None
        if args.log is not None:
            log_path = (
                default_inject_log_path(root)
                if args.log == "default"
                else (Path(args.log) if Path(args.log).is_absolute() else root / args.log)
            )
        return cmd_resolve(
            root,
            args.file,
            line=args.line,
            as_json=args.json,
            log_path=log_path,
        )

    if args.command == "bootstrap":
        from aal.bootstrap import (
            cmd_bootstrap_apply,
            cmd_bootstrap_migrate,
            cmd_bootstrap_suggest,
        )

        if args.bootstrap_cmd == "suggest":
            return cmd_bootstrap_suggest(root)
        if args.bootstrap_cmd == "migrate":
            return cmd_bootstrap_migrate(root, dry_run=not args.apply)
        return cmd_bootstrap_apply(root, level=args.level, dry_run=not args.apply)

    if args.command == "annotate":
        from aal.bootstrap import cmd_annotate

        return cmd_annotate(root, args.file, args.domain, dry_run=args.dry_run)

    if args.command == "doctor":
        from aal.doctor import cmd_doctor

        return cmd_doctor(root, strict=args.strict)

    if args.command == "hook":
        if args.hook_cmd == "cursor-pretooluse":
            from aal.cursor_hook import cmd_cursor_pretooluse

            return cmd_cursor_pretooluse(root)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
