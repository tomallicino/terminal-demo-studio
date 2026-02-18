# Releasing

## PyPI Trusted Publisher Setup

1. Create PyPI project: `terminal-demo-studio-cli`.
2. Add trusted publisher:
- Owner: `tomallicino`
- Repo: `terminal-demo-studio`
- Workflow: `publish.yml`
- Environment: `pypi`

## GitHub

1. Create environment `pypi` in repository settings.
2. Merge to default branch.
3. Tag release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The `publish` workflow builds and uploads package artifacts via OIDC.

## Release Gate Checklist

1. `ruff check .`
2. `mypy terminal_demo_studio`
3. `pytest tests -v`
4. `./scripts/release_preflight.sh`
5. `./scripts/readme_smoke.sh`
6. CI matrix must pass on Linux, macOS, and Windows (including scripted_vhs smoke on Windows).
7. Regenerate README media and verify no empty top header bar in any showcase GIF.

## Skill Publishing

No separate skill repository is required.

1. Keep `skills/terminal-demo-studio/SKILL.md` in this repo.
2. Ensure frontmatter `name` matches install name (`terminal-demo-studio`).
3. Users install with:

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```
