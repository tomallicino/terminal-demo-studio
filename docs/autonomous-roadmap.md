# Autonomous Complex-TUI Roadmap

This document tracks autonomous complex-TUI support across both runtime lanes.

## Current State

### `autonomous_video` (implemented)
- Purpose: deterministic, no-human, full-screen capture for modern TUIs.
- Runtime stack: `kitty` remote control + `Xvfb` + `ffmpeg`.
- User-facing lane alias: `visual` (`tds run/render --mode visual`).
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
- Safety controls (implemented):
  - setup/preinstall timeout (`TDS_SETUP_TIMEOUT_SECONDS`)
  - media redaction pipeline (`auto|off|input_line`) with safe defaults
  - failure bundle redaction for sensitive values (API keys/token-like values)
  - hardened Docker defaults (`cap-drop`, `no-new-privileges`, PID limit)
  - Kitty remote control constrained to `socket-only` with a private per-scenario socket directory
  - prompt-loop policies (`manual`, `approve`, `deny`) with bounded rounds and optional `allow_regex`
  - optional `allowed_command_prefixes` allowlist to scope what approve mode can confirm
  - fail-fast guidance when a manual prompt blocks a wait gate
  - policy linting that requires scoped `allow_regex` for approve mode and blocks unbounded approve regex by default
  - `tds lint` for preflight policy/action checks before execution

### `autonomous_pty` (implemented, command/assert focused)
- Purpose: command/assert closed-loop execution with textual snapshots.
- Supported primitives: command + waits/asserts + deterministic timing.
- Interactive `input`/`key`/`hotkey` is intentionally guarded and fails fast.

## Reliability Contract

1. No fuzzy heuristics: every transition is explicit action + wait/assert gate.
2. No silent skips: unsupported actions hard-fail with diagnostics.
3. Every failed run emits a debuggable bundle.
4. Determinism comes from pinned environment, stable anchors, and bounded waits.
5. Real-agent flows should include at least one independent side-effect verification gate (for example filesystem/test assertion outside the chat response surface).
6. Prefer verification commands that emit newline-terminated lines to keep prompt rendering stable in recorded output.

## Runtime Selection Policy

For `--mode autonomous_video`:

1. `--local`: local-only, strict dependency requirement.
2. `--docker`: container-only.
3. default: local first, Docker fallback.

If both local and Docker are unavailable, execution fails fast with install guidance.

## Prompt Loop Policy

- `--agent-prompts auto`: use screenplay/scenario policy.
- `--agent-prompts manual`: do not auto-confirm prompts.
- `--agent-prompts approve`: auto-approve when prompt regex matches.
- `--agent-prompts deny`: auto-deny when prompt regex matches.

Both `approve` and `deny` are bounded by `max_rounds`. `approve` can be constrained by both `allow_regex` and `allowed_command_prefixes`.

## Redaction Policy

- `--redact auto` (default): resolve from screenplay settings, then auto-detect sensitive actions.
- `--redact input_line`: force input-line masking in composed media.
- `--redact off`: disable media masking.
- Failure bundles are always value-redacted regardless of media mode.

## Roadmap

## P1
- Mouse event automation for TUIs that cannot be driven by keyboard only.
- Optional proxy/replay mode for deterministic network replays.
- Real-tool nightly stability suite with strict side-effect verification gates.
- Approval-aware helper blocks to reduce screenplay repetition for tools that request multiple confirmations.

## P2
- Richer state probes and adapter-specific readiness predicates.
- Nightly stress suites for advanced real-tool autonomous video demos.

## Claim Gate

Only claim “full autonomous complex-TUI support” when:

1. Key flows are stable under CI with deterministic mock demos.
2. At least one advanced real-tool demo is stable in nightly runs.
3. Failure bundles are sufficient to diagnose >95% of run failures without manual reproduction.
