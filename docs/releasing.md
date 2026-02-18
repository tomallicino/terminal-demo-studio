# Releasing

## PyPI Trusted Publisher Setup

1. Create PyPI project: `terminal-demo-studio-cli`.
2. Add trusted publisher:
   - Owner: `tomallicino`
   - Repo: `terminal-demo-studio`
   - Workflow: `publish.yml`
   - Environment: `pypi`

## GitHub Setup

1. Create repository environment `pypi`.
2. Merge to default branch.
3. Tag release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The publish workflow builds and uploads distributions via OIDC.

## Alpha Launch Checklist

- [ ] `ruff check .`
- [ ] `mypy terminal_demo_studio`
- [ ] `pytest tests -v`
- [ ] `./scripts/install_context_smoke.sh` (non-Windows)
- [ ] `./scripts/readme_smoke.sh` (Linux/macOS)
- [ ] `./scripts/release_preflight.sh` (non-Windows)
- [ ] README wow path is valid (`pipx install` + one-command `tds render`)
- [ ] Six golden templates validate and scripted-render smoke successfully
- [ ] Reusable GitHub action smoke passes in CI (`.github/actions/render`)
- [ ] `docs/reproducibility.md` and stable/experimental messaging are accurate
- [ ] Windows scripted CI parity remains explicitly documented as deferred

## Skill Publishing

No separate skill repository is required.

1. Keep `skills/terminal-demo-studio/SKILL.md` in this repo.
2. Keep frontmatter `name: terminal-demo-studio`.
3. Remote install command:

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

## Post-Publish Smoke

After publish completes:

```bash
python -m pip install --upgrade pip
pip install terminal-demo-studio-cli
tds render --template install_first_command --output gif --output-dir outputs
```
