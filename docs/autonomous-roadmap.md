# Autonomous Runtime Roadmap

Status and roadmap for autonomous lanes.

## Current state

## `autonomous_pty` (stable command/assert lane)

- Purpose: deterministic command execution with wait/assert checks.
- Supported: `command`/`type`, waits, assertions, `expect_exit_code`, timing controls.
- Explicitly unsupported: `input`, `key`, `hotkey` (fails fast with actionable reason).
- Artifacts: `runtime/events.jsonl`, `summary.json`, `failure/*`.

## `autonomous_video` (experimental visual lane)

- Purpose: deterministic full-screen interactive capture for modern TUIs.
- Runtime stack: `kitty` + `Xvfb` + `ffmpeg` (local or Docker fallback).
- Supported primitives:
  - `command` / `type`
  - `input`
  - `key` / `hotkey`
  - `wait_for`, `wait_screen_regex`, `wait_line_regex`
  - `assert_screen_regex`, `assert_not_screen_regex`
  - `sleep`, `wait_stable`
- Prompt-loop controls:
  - modes: `manual`, `approve`, `deny`
  - regex prompt detection + optional allow-regex
  - optional `allowed_command_prefixes`
  - bounded rounds (`max_rounds`)
- Redaction:
  - media: `auto`, `off`, `input_line`
  - failure bundle sensitive-value redaction is always on

## Reliability contract

1. Unsupported actions fail loudly.
2. Every failure produces a diagnosable bundle.
3. Prompt automation is policy-scoped and bounded.
4. Determinism comes from explicit waits/assertions, not heuristics.

## Planned work

## P1

- Mouse automation for TUIs that require pointer interaction.
- More adapter-aware readiness predicates for visual mode.
- Broader deterministic mock fixture suite for edge interaction cases.

## P2

- Nightly stress suite for longer autonomous video sessions.
- Expanded diagnostics for prompt-loop policy mismatch scenarios.

## Claim gate for “full autonomous complex-TUI support”

Only claim full support when all are true:

1. Stable CI coverage for complex mock flows.
2. Stable nightly real-tool flow(s) with independent side-effect verification.
3. Failure bundle quality is high enough for >95% first-pass triage.
