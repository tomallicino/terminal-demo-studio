# Architecture

`terminal-demo-studio` has three execution lanes with one shared artifact contract.

## High-Level Flow

1. `tds` receives command (`render`, `run`, `new`, `init`, `validate`, `doctor`, `debug`).
2. Screenplay is loaded and validated (`models.py`) with variable interpolation.
3. Lane selection is resolved from `--mode` or screenplay scenarios.
4. Canonical run layout is created (`artifacts.py`).
5. Lane execution runs and emits media/events/summary/failure artifacts.
6. CLI prints machine-friendly keys (`STATUS`, `RUN_DIR`, `MEDIA_*`, `SUMMARY`, `EVENTS`).

## Core Modules

- `terminal_demo_studio/cli.py`
  - command routing, mode policy, local/docker fallback handling.
- `terminal_demo_studio/models.py`
  - screenplay schema, validation, interpolation.
- `terminal_demo_studio/resources.py`
  - packaged template discovery/loading.
- `terminal_demo_studio/artifacts.py`
  - run directory layout + manifest/summary writers.
- `terminal_demo_studio/tape.py`
  - VHS tape compiler.
- `terminal_demo_studio/director.py`
  - scripted VHS lane orchestration.
- `terminal_demo_studio/editor.py`
  - split-screen composition + GIF output + label rendering fallback.
- `terminal_demo_studio/runtime/runner.py`
  - `autonomous_pty` command/assert runtime.
- `terminal_demo_studio/runtime/video_runner.py`
  - `autonomous_video` runtime for interactive capture (experimental).
- `terminal_demo_studio/runtime/shells.py`
  - cross-platform shell launcher logic.
- `terminal_demo_studio/doctor.py`
  - mode-aware diagnostics with actionable `NEXT:` guidance.
- `terminal_demo_studio/docker_runner.py`
  - optional dockerized execution.

## Execution Lanes

### `scripted_vhs` (stable)

- Deterministic playback from compiled tapes.
- Supports composed multi-pane outputs and showcase-friendly GIF/MP4 assets.

### `autonomous_pty` (stable, command/assert scope)

- Closed-loop setup/command execution with wait/assert checks.
- Writes runtime events and failure bundles.
- Interactive primitives (`input`/`key`/`hotkey`) are currently guarded.

### `autonomous_video` (experimental)

- Interactive full-screen capture lane via Kitty + virtual display stack.
- Intended for complex TUI-style automation with visual output capture.
- Not promoted as stable in README quickstart.

## Canonical Run Artifact Layout

For all lanes:

- `run_dir/manifest.json`
- `run_dir/summary.json`
- `run_dir/media/*.gif|*.mp4`
- `run_dir/scenes/scene_*.mp4` (scripted lane)
- `run_dir/tapes/scene_*.tape` (scripted lane)
- `run_dir/runtime/events.jsonl` (autonomous lanes)
- `run_dir/failure/*` on failure

## Debug Flow

- `tds render/run` prints machine-readable paths.
- `tds debug <run_dir>` provides compact operator summary.
- `tds debug <run_dir> --json` emits stable JSON for agent workflows.

## Distribution Surface

- Python package: `terminal_demo_studio`
- PyPI distribution: `terminal-demo-studio`
- CLI binary: `tds`
- Skill: `skills/terminal-demo-studio/SKILL.md`
- Reusable GitHub Action: `.github/actions/render`
