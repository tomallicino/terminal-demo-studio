# Autonomous Complex-TUI Roadmap

This document tracks autonomous complex-TUI support across both runtime lanes.

## Current State

### `autonomous_video` (implemented)
- Purpose: deterministic, no-human, full-screen capture for modern TUIs.
- Runtime stack: `kitty` remote control + `Xvfb` + `ffmpeg`.
- Supported primitives:
  - `command`/`type`: send text + Enter.
  - `input`: send text without Enter.
  - `key`/`hotkey`: `send-key` through Kitty remote control.
  - `wait_for`, `wait_screen_regex`, `wait_line_regex`: regex-gated waits.
  - `assert_screen_regex`, `assert_not_screen_regex`.
  - `sleep`, `wait_stable`.
- Unsupported in this lane:
  - `expect_exit_code` (fails explicitly with guidance).
  - mouse automation (P1).
- Artifacts:
  - `runtime/events.jsonl`
  - `summary.json`
  - `failure/reason.txt`, `failure/screen.txt`, `failure/step.json`, `failure/video_runner.log`

### `autonomous_pty` (implemented, command/assert focused)
- Purpose: command/assert closed-loop execution with textual snapshots.
- Supported primitives: command + waits/asserts + deterministic timing.
- Interactive `input`/`key`/`hotkey` is intentionally guarded and fails fast.

## Reliability Contract

1. No fuzzy heuristics: every transition is explicit action + wait/assert gate.
2. No silent skips: unsupported actions hard-fail with diagnostics.
3. Every failed run emits a debuggable bundle.
4. Determinism comes from pinned environment, stable anchors, and bounded waits.

## Runtime Selection Policy

For `--mode autonomous_video`:

1. `--local`: local-only, strict dependency requirement.
2. `--docker`: container-only.
3. default: local first, Docker fallback.

If both local and Docker are unavailable, execution fails fast with install guidance.

## Roadmap

## P1
- Mouse event automation for TUIs that cannot be driven by keyboard only.
- Optional proxy/replay mode for deterministic network replays.
- Secret-aware redaction helpers for recorded video workflows.

## P2
- Richer state probes and adapter-specific readiness predicates.
- Nightly stress suites for advanced real-tool autonomous video demos.

## Claim Gate

Only claim “full autonomous complex-TUI support” when:

1. Key flows are stable under CI with deterministic mock demos.
2. At least one advanced real-tool demo is stable in nightly runs.
3. Failure bundles are sufficient to diagnose >95% of run failures without manual reproduction.
