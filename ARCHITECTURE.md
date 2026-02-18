# Architecture

`terminal-demo-studio` has two execution lanes that share one output contract: media and diagnostics are always derived from executed sessions.

## High-Level Flow

1. CLI accepts `run`, `validate`, `new`, `doctor`.
2. Screenplay is loaded, normalized, and interpolated (`tmp_dir` injected automatically).
3. Run path selection:
- `scripted_vhs`: compile tape and render via VHS/ffmpeg pipeline.
- `autonomous_pty`: execute command/assert closed-loop actions and produce run artifacts.
4. Optional composition step outputs MP4/GIF.
5. Artifacts are written to output directory and `.terminal_demo_studio_runs/`.

## Core Modules

- `terminal_demo_studio/cli.py`: command routing and mode selection.
- `terminal_demo_studio/models.py`: screenplay schema v2, validation, interpolation inputs.
- `terminal_demo_studio/tape.py`: VHS tape compilation, key/hotkey/wait support for scripted lane.
- `terminal_demo_studio/director.py`: scripted lane render orchestration.
- `terminal_demo_studio/editor.py`: split-screen composition and GIF export.
- `terminal_demo_studio/runtime/runner.py`: autonomous command/assert execution and artifact emission.
- `terminal_demo_studio/runtime/waits.py`: wait/assert timing utilities.
- `terminal_demo_studio/runtime/shells.py`: cross-platform shell command construction.
- `terminal_demo_studio/adapters/base.py`: adapter interface + built-ins (`generic`, `shell_marked`).
- `terminal_demo_studio/doctor.py`: local + docker diagnostics.

## Execution Modes

- `--mode scripted_vhs`: deterministic cinematic playback.
- `--mode autonomous_pty`: closed-loop command/assert execution with assertions/failure bundles.
- `--mode auto`: inferred from screenplay scenarios.

Current limit: interactive key/hotkey/input actions are not yet implemented in the autonomous lane.

## Run Artifacts

Autonomous runs emit:

- `events.jsonl`
- `summary.json`
- `failure/` with `screen.txt` and `reason.txt` on failure

## Repository Layout

- Package: `terminal_demo_studio/`
- Built-in templates: `terminal_demo_studio/templates/`
- Mock demos: `examples/mock/`
- Advanced real-tool demos: `examples/real/`
- Public media: `docs/media/`
- Skill: `skills/terminal-demo-studio/SKILL.md`
