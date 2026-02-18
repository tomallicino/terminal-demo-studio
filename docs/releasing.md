# Releasing

Release flow for `terminal-demo-studio` on PyPI + GitHub.

## PyPI trusted publisher setup

1. Create PyPI project `terminal-demo-studio`.
2. Add trusted publisher:
- Owner: `tomallicino`
- Repository: `terminal-demo-studio`
- Workflow: `publish.yml`
- Environment: `pypi`

## GitHub setup

1. Create a `pypi` environment in repository settings.
2. Ensure `.github/workflows/publish.yml` targets that environment.
3. Tag a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Pre-release checklist

- `ruff check .`
- `mypy terminal_demo_studio`
- `pytest tests -v`
- `tds validate examples/showcase/onboarding_tokyo_neon.yaml --explain`
- `tds lint examples/showcase/autonomous_codex_real_short.yaml --strict`
- `./scripts/install_context_smoke.sh` (non-Windows)
- `./scripts/readme_smoke.sh` (Linux/macOS)
- `./scripts/release_preflight.sh` (non-Windows)
- `./scripts/render_showcase_media.sh` (refresh gallery media)

## Post-release smoke

```bash
python -m pip install --upgrade pip
pip install terminal-demo-studio
tds render --template install_first_command --output gif --output-dir outputs
```

## Skill publishing

Skill is versioned in this repo:

- `skills/terminal-demo-studio/SKILL.md`

Install command:

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

## Release hygiene notes

- Keep README command examples aligned with actual `tds --help` output.
- Keep `CAPABILITIES.md` evidence links current as tests evolve.
- Keep showcase assets in `docs/media` synced with screenplay sources in `examples/showcase`.
