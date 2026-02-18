# Architecture

`terminal-demo-studio` is a deterministic rendering pipeline with three execution lanes and one shared artifact contract.

## System view

1. `tds` parses command + options (`render`, `run`, `validate`, `lint`, `new`, `init`, `doctor`, `debug`).
2. Screenplay YAML is loaded and validated (`models.py`), including variable interpolation.
3. Lane resolution chooses `scripted_vhs`, `autonomous_pty`, or `autonomous_video`.
4. A canonical run layout is created (`artifacts.py`).
5. Lane runtime executes and writes media/events/summaries.
6. CLI emits machine-readable result keys (`STATUS`, `RUN_DIR`, `MEDIA_*`, `SUMMARY`, `EVENTS`).

## Lane architecture

## `scripted_vhs` (stable)

- Screenplay actions are compiled into VHS tape directives (`tape.py`).
- Scene videos are rendered and stitched into final compositions (`director.py`, `editor.py`).
- Split-screen composition supports sequential or simultaneous playback.
- Label rendering uses FFmpeg drawtext when available, with Pillow image-overlay fallback.

## `autonomous_pty` (stable command/assert lane)

- Executes setup + command actions in PTY-like shell flow (`runtime/runner.py`).
- Supports waits/assertions (`wait_for`, regex waits/assertions, `expect_exit_code`).
- Rejects interactive primitives (`input`, `key`, `hotkey`) with explicit failure reasons.
- Writes runtime events (`runtime/events.jsonl`) and failure bundles.

## `autonomous_video` (experimental)

- Runs full-screen terminal UI capture (`runtime/video_runner.py`).
- Supports `command`, `input`, `key`, `hotkey`, waits/assertions, and prompt-loop policies.
- Applies policy linting and optional command-prefix allowlisting before automated approvals.
- Supports media redaction modes (`auto`, `off`, `input_line`) and value-redacted failure bundles.
- Chooses local runtime when dependencies exist, otherwise falls back to Docker (auto mode).

## Core components

- `terminal_demo_studio/cli.py`: command routing, mode normalization, render orchestration.
- `terminal_demo_studio/models.py`: screenplay schema + validation.
- `terminal_demo_studio/interpolate.py`: variable interpolation.
- `terminal_demo_studio/resources.py`: packaged template discovery and loading.
- `terminal_demo_studio/linting.py`: static screenplay checks.
- `terminal_demo_studio/prompt_policy.py`: merge + lint for agent prompt policies.
- `terminal_demo_studio/redaction.py`: media redaction mode resolution.
- `terminal_demo_studio/doctor.py`: dependency and runtime diagnostics.
- `terminal_demo_studio/docker_runner.py`: Docker execution, image lifecycle, hardening knobs.

## Artifact contract

Every run writes a canonical directory:

- `manifest.json`
- `summary.json`
- `media/*.gif|*.mp4`
- `scenes/scene_*.mp4` and `tapes/scene_*.tape` (scripted lane)
- `runtime/events.jsonl` (autonomous lanes)
- `failure/*` on failure

The contract is intentionally lane-agnostic so CI jobs and agents can parse results uniformly.

## Runtime selection policy

For `--mode auto`:

- If screenplay contains any `autonomous_video` scenario, run `autonomous_video`.
- Else if screenplay contains any `autonomous_pty` scenario, run `autonomous_pty`.
- Else run `scripted_vhs`.

Runtime location behavior:

- `--local`: strict local execution.
- `--docker`: strict Docker execution when supported.
- default/auto: lane-aware fallback (`scripted_vhs` and `autonomous_video` can use Docker fallback; `autonomous_pty` remains local).

## Operational interfaces

- `tds doctor`: mode-aware dependency checks with `NEXT:` remediation hints.
- `tds lint`: static guardrail checks without running demos.
- `tds debug`: compact or JSON triage output from run summaries.

## Packaging and distribution

- Package name: `terminal-demo-studio`
- Python module: `terminal_demo_studio`
- CLI binary: `tds`
- Skill entrypoint: `skills/terminal-demo-studio/SKILL.md`
- Reusable CI action: `.github/actions/render/action.yml`
