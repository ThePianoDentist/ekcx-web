# AGENTS.md

When editing AGENTS.md: stay very concise. No fluff, examples, or restating other docs.

## Style

- Docs: super concise.
- Files <1000 lines (ideally <500); suggest splits.
- Favour simplicity; avoid complex language features.
- Comments explain *why*, never *what*.

## Testing

- Pytest fixtures for most setup; **polyfactory** for data.
- Each test: `# Setup:` / `# Run:` / `# Check:`.
- Minimal mocking; prefer intermediate/e2e-ish tests of whole chunks.

## Workflow

- After each task: fix docs if they drifted.
- `git pull` main before branching; tests green before `git push`.
- Before every `git push`: run [pre-push](.cursor/skills/pre-push/SKILL.md) (secrets + security sweep). Never push secrets; scrub them from *all* commits first.
- Prefer `uv` / `make` (see README).
- SQLite-compatible SQL only.

## Layout

Vertical slices under `app/` (not `src/`): **data** / **domain** / **interfaces**.

```
app/<slice>/{data,domain,interfaces/{web,admin,scripts}}/
docs/  tests/  results/   # raw race files at repo root, not in data/
```

- **data**: read/write only. **domain**: business logic (no HTTP/CLI). **interfaces**: validate → domain → respond.
- Slices: `results`, `standings`, `events`, `riders`. Details: [docs/architecture.md](docs/architecture.md).
