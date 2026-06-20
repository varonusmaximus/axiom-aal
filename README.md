# axiom-aal

Agent Annotation Language (AAL) — parse `# @!domain` annotations, resolve domain skills, inject context via Cursor hooks, and verify registry integrity.

Extracted from [axiompy](https://github.com/varonusmaximus/axiompy) at commit `ca9fb06d06fb24db5f601c60a8714f0dadb37191`.

## Install

```bash
pip install axiom-aal
# or from source:
pip install -e ".[dev]"
```

## CLI

```bash
aal doctor --strict
aal verify-domains --strict
aal resolve --file path/to/file.py --line 1 --json
aal install --project --hooks --force
aal hook cursor-pretooluse   # Cursor preToolUse adapter (stdin JSON)
```

## Consumer repos (e.g. axiompy)

AAL installs **hooks, aal.yaml, aal.mdc, and CI template only**. Each consumer owns:

| Artifact | Owner |
|----------|-------|
| `.cursor/domains.yaml`, `.cursor/bootstrap.yaml` | Consumer repo |
| `.cursor/skills/**` | Consumer skills bundle (e.g. `axiompy-skills --project`) |
| `# @!domain` annotations | Consumer source files |

**axiompy bootstrap:**

```bash
pip install -e ".[dev]"       # axiompy
pip install axiom-aal         # AAL engine
axiompy-skills --project      # sync skills to .cursor/skills/
aal install --project --hooks --force
aal doctor --strict
aal verify-domains --strict
```

## Docs

See [docs/spec.md](docs/spec.md) and [docs/deployment.md](docs/deployment.md).

## License

MIT


## Publish to GitHub

```bash
gh auth login
gh repo create varonusmaximus/axiom-aal --public --source=. --remote=origin --push
git push --tags
```

Enable branch protection on `main` (require PR + `ci` status check).
