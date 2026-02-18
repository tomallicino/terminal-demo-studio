## Summary

- What changed:
- Why:

## Alpha Launch Gate (must be complete before announcement)

- [ ] CLI is `tds` only (no public `studio` command usage)
- [ ] README top section includes one-command wow flow and embedded output media
- [ ] Stable artifact layout + `tds debug` contract verified
- [ ] Reusable render action (`.github/actions/render`) works with CI smoke
- [ ] 6 golden templates shipped and render/validate smoke-covered
- [ ] Reproducibility contract documented (`docs/reproducibility.md`)
- [ ] Stable vs experimental lane messaging is explicit and accurate
- [ ] Windows scripted CI parity status is explicitly documented as deferred
- [ ] Release preflight passes (privacy + forbidden file checks)

## Validation

- [ ] `ruff check .`
- [ ] `mypy terminal_demo_studio`
- [ ] `pytest tests -v`
- [ ] `./scripts/install_context_smoke.sh` (non-Windows)
- [ ] `./scripts/readme_smoke.sh` (Linux/macOS)
- [ ] `./scripts/release_preflight.sh` (non-Windows)

## Known Limitations (if any)

- 
