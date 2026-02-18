---
name: terminal-demo-studio
description: Build deterministic terminal demo media with portable screenplay defaults, canonical run artifacts, and agent-friendly debug outputs.
---

# terminal-demo-studio

Use this skill when you need to create, validate, render, and debug terminal/TUI demo media.

## Install

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

## Fast path

```bash
pipx install terminal-demo-studio
tds render --template install_first_command --output gif --output-dir outputs
```

Capture structured outputs from stdout:

- `STATUS`
- `RUN_DIR`
- `MEDIA_GIF` / `MEDIA_MP4`
- `SUMMARY`
- `EVENTS` (autonomous lanes)

## Recommended workflow

```bash
tds new demo_case --template before_after_bugfix --destination screenplays
tds validate screenplays/demo_case.yaml --explain
tds lint screenplays/demo_case.yaml
tds render screenplays/demo_case.yaml --mode scripted_vhs --local --output gif --output mp4 --output-dir outputs
tds debug <run_dir>
```

## Lane selection

1. `scripted_vhs`
- best for deterministic marketing/docs media.
- supports split-screen composition and themed rendering settings.

2. `autonomous_pty`
- best for command/assert verification workflows.
- interactive key/input primitives are intentionally unsupported.

3. `autonomous_video`
- best for interactive full-screen TUI capture.
- supports `agent_prompts` modes (`manual`, `approve`, `deny`) and policy linting.

## Safety defaults

- Run `tds lint <screenplay> --strict` for autonomous-video screenplays.
- Use explicit `wait_for` / regex assertions at critical transitions.
- Keep approval policies scoped (avoid unbounded allow patterns).
- Use `--redact auto` unless you have a specific reason to disable masking.

## Debug loop

```bash
tds debug <run_dir>
tds debug <run_dir> --json
```

Use the JSON mode for agent triage and retry planning.

## Showcase media pipeline

This repo ships a curated multi-theme gallery:

- Screenplays: `examples/showcase/*.yaml`
- Batch render script: `scripts/render_showcase_media.sh`
- Generated assets: `docs/media/*.gif` and `docs/media/*.mp4`

Refresh gallery media:

```bash
./scripts/render_showcase_media.sh
```
