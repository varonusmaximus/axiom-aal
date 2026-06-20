# AxiomPy ↔ AAL mapping

Bridge document between the portable AAL spec and this repository's implementation.

## Package and CLI

| AAL concept | AxiomPy implementation |
|-------------|------------------------|
| `pip install agentic-aal` | `pip install axiom-aal` |
| `aal` CLI | `aal` (extended with AAL subcommands) |
| `aal install --hooks` | `aal install --project --hooks` |
| `aal upgrade` | `aal upgrade --force` |
| `aal verify-domains` | `aal verify-domains --strict` |
| `aal resolve` | `aal resolve --file PATH --line N --json` |
| `aal resolve (logged)` | `aal resolve --file PATH --line N --log` |
| `aal bootstrap suggest` | `aal bootstrap suggest` |
| `aal bootstrap apply --level file` | `aal bootstrap apply --level file --apply` |
| `aal bootstrap migrate` | `aal bootstrap migrate --apply` |
| `aal annotate FILE --domain D` | `aal annotate FILE --domain D` |
| `aal doctor --strict` | `aal doctor --strict` |
| `aal hook (Cursor)` | `aal hook cursor-pretooluse` |

Python API: `aal` (`parser`, `verify`, `resolve`, `middleware`, `cursor_hook`, `bootstrap`).

## Registry layout (`.cursor/` first)

| AAL spec path | AxiomPy path |
|---------------|--------------|
| `.agent/domains.yaml` | `.cursor/domains.yaml` |
| `.agent/domains.local.yaml` | `.cursor/domains.local.yaml` |
| `.agent/aal.yaml` | `.cursor/aal.yaml` |
| `.agent/bootstrap.yaml` | `.cursor/bootstrap.yaml` |
| `.agent/.aal-manifest.json` | `.cursor/.axiompy-manifest.json` |
| `.agent/skills/*.md` | `.cursor/skills/<domain>/SKILL.md` |
| `{stem}.override.md` | `.cursor/skills/<domain>.override/SKILL.md` |

## Function domains vs skill packages

Annotations use **function domain** names (what the code does). Inject composes **shared packages** and **domain skill folders** — there is no `@include` syntax inside markdown.

| Layer | Path | Role |
|-------|------|------|
| Shared packages | `.cursor/skills/code-style/`, `design-patterns/`, … | Cross-cutting practice (formatting, factories, security review) |
| Domain skills | `.cursor/skills/storage/`, `io/`, `secrets/`, … | Domain-only rules in `SKILL.md` |
| Sidecars | Same folder as domain `SKILL.md` (e.g. `mcp/tools-sessions.md`) | Auto-merged by `merge_skill_content` at inject |
| Registry | `.cursor/domains.yaml` | Lists `SKILL.md` paths only — **not** sidecar paths |

### How composition works

1. `# @!storage` on a file selects the **storage** domain.
2. `domains.yaml` lists shared packages plus `.cursor/skills/storage/SKILL.md`.
3. Resolve loads each listed `SKILL.md` and **automatically appends** other `*.md` files in that folder (sidecars).
4. Domain skill text should be **domain-only** — shared factory/settings rules live in `design-patterns`, not repeated in domain files.

Example registry entry:

```yaml
storage:
  skills:
    - .cursor/skills/code-style/SKILL.md
    - .cursor/skills/design-patterns/SKILL.md
    - .cursor/skills/storage/SKILL.md   # sql.md sidecar auto-included
```

Injected paths for `# @!storage` on `axiompy/io/database.py`:

```
.cursor/skills/code-style/SKILL.md
.cursor/skills/design-patterns/SKILL.md
.cursor/skills/storage/SKILL.md  (+ storage/sql.md merged inside)
```

### Domain → composition matrix

| Domain | Shared packages | Domain folder |
|--------|-----------------|---------------|
| `core` | code-style | `core/` |
| `io` | code-style, design-patterns | `io/` |
| `storage` | code-style, design-patterns | `storage/` |
| `object` | code-style, design-patterns | `object/` |
| `rpc` | code-style, design-patterns | `rpc/` |
| `servers` | code-style, design-patterns | `servers/` |
| `mcp` | code-style, design-patterns, code-review | `mcp/` |
| `secrets` | code-style, design-patterns, code-review | `secrets/` |
| `tooling` | code-style, design-patterns, testing | `tooling/` |
| `testing` | code-style | `testing/` |
| `documentation` | code-style | `documentation/` |
| `delivery` | code-style, ship-it, testing | `delivery/` |

> **FIXME:** `io` is intentionally broad (HTTP, files, serialization, web). Split into `http`, `file`, and `serialization` domains later.

Source of truth: `bundles/axiompy_skills/` (synced to `.cursor/skills/` on install).

### Inject log (review)

Every hook inject appends one JSONL line to **`.cursor/logs/aal-inject.jsonl`** (configurable via `inject_log` in `.cursor/aal.yaml`). Each record includes timestamp, file, line, domains, skill paths, and full `resolve` payload.

```bash
# Manual resolve with log (same path as hook)
aal resolve --file axiompy/servers/mcp_service.py --line 1 --log

# Review latest entries
tail -3 .cursor/logs/aal-inject.jsonl | python3 -m json.tool

# Pretty-print one line
tail -1 .cursor/logs/aal-inject.jsonl | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2)[:2000])"
```

The log file is gitignored (`.cursor/logs/`).

## Templates package

AAL install templates ship in `bundles/aal_templates/` (wheel-bundled as `aal_templates`).

## Open decisions resolved

1. **Registry host:** `.cursor/` first; future host-agnostic `.axiompy/` extraction documented in [HLD.md](./HLD.md) §7.
2. **Skills format:** Cursor `SKILL.md` folder trees (not flat `.md` files).
3. **CLI surface:** Extend `aal` rather than a separate `axiompy-aal` entry point.
4. **Composition:** `domains.yaml` playlists shared + domain `SKILL.md` paths; sidecars auto-merge — no in-file includes.

## Source of truth

| Layer | File |
|-------|------|
| Narrative / onboarding | [HLD.md](./HLD.md) |
| Normative spec | [spec.md](./spec.md) |
| Runbooks | [deployment.md](./deployment.md) |
| Behavior | `axiompy/aal/` + `axiompy/cli/cursor_skills.py` |

If code and docs disagree after MVP, **code wins** — update `spec.md` in the same PR.
