# Autonomous Complex-TUI Roadmap

## Current v1 Scope

`autonomous_pty` is reliable for command/assert-driven automation:

1. Run commands.
2. Evaluate waits/assertions.
3. Emit event log, summary, and failure bundle.

Current limit: interactive `input`, `key`, and `hotkey` actions are intentionally blocked in autonomous mode to avoid false-positive runs.

## v1.1: True Interactive Session Core

1. Keep one persistent PTY session per scenario.
2. Implement action injectors:
- send text without auto-enter (`input`)
- send key sequences (`key`)
- send chorded keys (`hotkey`)
3. Parse terminal stream incrementally and maintain screen state snapshots.
4. Add cross-platform PTY adapters:
- POSIX: `pty`/`select` runner
- Windows: ConPTY-backed runner

## v1.2: Reliability Layer

1. Semantic wait stack:
- prompt-mark waits when present
- screen/line regex waits
- stable-screen waits
2. Bounded retry policy per step with deterministic backoff windows.
3. Adapter hooks for tool-specific state probes and normalization.
4. Failure bundles upgraded with:
- recent raw stream tail
- failing step/action payload
- time budget and retry counters

## v1.3: Advanced Real-Tool Readiness

1. Add a canonical real-tool fixture with pinned versions.
2. Add OS matrix nightly stress runs for autonomous real demos.
3. Define SLO targets:
- success rate
- median runtime
- flake budget
4. Publish supported adapters and known limitations table.

## Release Gate for “Complex TUI Autonomous” Claim

Only claim full complex-TUI autonomous support when all are true:

1. Interactive actions (`input`/`key`/`hotkey`) are implemented and CI-verified on macOS/Linux/Windows.
2. At least one real complex TUI demo passes in nightly runs with bounded flake.
3. Failure bundles consistently identify failing steps and remediation hints.
