---
name: terminal-demo-studio
description: Build deterministic terminal demo media with portable mock defaults, canonical run artifacts, and agent-friendly debug outputs.
---

# terminal-demo-studio

Use this skill to create terminal demos that are reproducible and easy to automate.

## Install (Remote-First)

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

## Default Onboarding (Portable First)

```bash
pipx install terminal-demo-studio
tds render --template install_first_command --output gif --output-dir outputs
```

Then inspect output paths from the command response (`RUN_DIR=...`, `MEDIA_GIF=...`).

## Core Workflow

```bash
tds new demo_case --template before_after_bugfix --destination screenplays
tds validate screenplays/demo_case.yaml --explain
tds render screenplays/demo_case.yaml --mode scripted_vhs --local --output gif --output-dir outputs
tds debug <run_dir>
```

## Modes

1. `scripted_vhs` (stable)
- deterministic cinematic rendering.
- default for showcase media.

2. `autonomous_pty` (stable, command/assert scope)
- closed-loop command/assert execution with `events.jsonl`, `summary.json`, failure bundles.
- use for agent verification workflows.

3. Autonomous interactive (`input`/`key`/`hotkey` in runtime lane)
- experimental and roadmap-tracked in `docs/autonomous-roadmap.md`.

## Advanced Real-Tool Lane

Use `examples/real/` only for advanced demos with explicit prerequisites.

Rules:
1. Keep README/public onboarding on portable mock demos.
2. Use explicit assertions/waits; do not rely on implicit timing.
3. Treat retries and timeouts as screenplay policy.

## Anti-Flake Checklist

1. Prefer `assert_screen_regex` and `wait_screen_regex` at key state boundaries.
2. Keep each action focused; avoid giant chained shell commands.
3. Preserve deterministic settings (theme, geometry, playback mode).
4. Use `tds debug --json` for machine-triage loops.
