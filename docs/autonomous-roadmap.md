# Autonomous Complex-TUI Specification (v1.1 Target)

This document is the implementation-ready specification for true interactive autonomy in `autonomous_pty`.

## 1. Scope and Guarantees

### 1.1 Goal
Execute complex terminal UIs reliably using explicit actions, waits, assertions, and adapter semantics across macOS, Linux, and Windows.

### 1.2 Non-goals
- Universal inference of expected input type from raw terminal bytes.
- Best-effort "continue anyway" behavior when state cannot be proven.

### 1.3 Reliability contract
- Reliability comes from deterministic orchestration primitives plus bounded retries.
- Every run emits artifacts that explain success/failure without manual guesswork.
- No silent skip behavior for unsupported primitives.

## 2. Runtime Architecture

### 2.1 Session model
- One persistent PTY session per scenario.
- Scenario actions execute against the same live terminal state.
- Session lifecycle: `spawn -> execute -> finalize -> artifact flush`.

### 2.2 Step state machine
Each action step transitions through:
1. `pending`
2. `dispatched`
3. `waiting`
4. `asserting`
5. terminal state: `passed | failed | timed_out`

### 2.3 Required run artifacts
- `events.jsonl`: ordered event stream (step transitions, waits, retries, adapter notes).
- `summary.json`: run metadata, timing, pass/fail counts, exit status.
- `failure/` bundle on error:
  - `reason.txt`
  - `screen.txt`
  - `stream_tail.txt`
  - `step.json`
  - `timing.json`

## 3. Schema Extensions (Backward Compatible)

Extends `terminal_demo_studio/models.py` while preserving current v2 fields.

### 3.1 Step-level controls
- `id: str | null`
- `timeout: <duration>`
- `retries: int >= 0`
- `retry_backoff: <duration>`
- `on_timeout: fail | retry | continue` (default `fail`)

### 3.2 Scenario-level controls
- `execution_mode: scripted_vhs | autonomous_pty`
- `shell: auto | bash | zsh | fish | pwsh | cmd`
- `adapter: generic | shell_marked | <adapter_id>`
- `determinism: strict | bounded` (default `strict` for mock demos)
- `time_budget: <duration>`

### 3.3 Validation rules
- Reject illegal combinations (`on_timeout=retry` with `retries=0`, etc.).
- Require explicit `timeout` when `retries > 0`.
- Reject unknown adapter IDs with actionable message.
- Keep legacy `type/wait_for` behavior valid.

## 4. Cross-Platform PTY Backends

### 4.1 POSIX backend
File: `terminal_demo_studio/runtime/pty_posix.py`
- Use `pty` with nonblocking reads.
- Use monotonic timing for wait budgets.
- Support terminal resize events.

### 4.2 Windows backend
File: `terminal_demo_studio/runtime/pty_windows.py`
- Use ConPTY via stable binding layer.
- Dedicated reader thread model to avoid pipe deadlocks.
- Explicit resize and teardown parity with POSIX backend.

### 4.3 Shell launcher abstraction
File: `terminal_demo_studio/runtime/shells.py`
- Windows default shell: PowerShell (`pwsh`/`powershell`).
- POSIX default shell: `bash`, fallback `sh`.
- `shell=cmd` supported on Windows by explicit request.

## 5. Wait and Assert Engine

### 5.1 Evaluation priority
1. Explicit assertions (`assert_screen_regex`, `assert_not_screen_regex`, exit-code checks)
2. Screen/line regex waits
3. Stable-screen waits
4. Semantic prompt markers (when available)

### 5.2 Deterministic timing model
- Monotonic clock only.
- Explicit timeout accounting per step and per scenario.
- No hidden extension of timeouts.

### 5.3 Retry policy
- Bounded retries only.
- Retry windows use deterministic backoff.
- Non-idempotent retries disabled unless explicitly enabled by adapter policy.

## 6. Adapter Contract

File: `terminal_demo_studio/adapters/base.py`

### 6.1 Required interface
- `probe_state(screen, stream_tail, context) -> dict`
- `normalize_screen(screen) -> str`
- `guard_action(action, state) -> GuardResult`
- `ready_predicates(action, state) -> list[Predicate]`
- `exit_predicates(state) -> list[Predicate]`

### 6.2 Built-ins
- `generic`: regex/stability only.
- `shell_marked`: uses prompt markers when shell integration is present.

### 6.3 Adapter invariants
- Must not suppress terminal errors.
- Must log normalization/guard decisions into events.
- Must provide deterministic behavior under the same input stream.

## 7. Input Semantics

### 7.1 Primitive behavior
- `command`: send text then Enter.
- `input`: send raw text without Enter.
- `key`: send normalized key token.
- `hotkey`: send normalized key chord.

### 7.2 Unsupported key behavior
If a key/chord is unsupported on active backend:
- Hard fail that step.
- Record backend, unsupported token, and suggested replacement in failure bundle.

## 8. Reliability Targets and Release Gates

### 8.1 Portable mock demos
- Determinism policy: `strict`.
- CI retries allowed: 0.
- SLO: >= 99.9% pass across OS matrix.

### 8.2 Advanced real-tool demos
- Determinism policy: `bounded`.
- Retries allowed: bounded per screenplay.
- SLO: >= 95% nightly pass within defined flake budget.

### 8.3 Claim gate for "complex TUI autonomous"
Only claim full interactive autonomous support when all are true:
1. `input`/`key`/`hotkey` implemented and tested on macOS/Linux/Windows.
2. Failure bundles contain complete step + screen + stream diagnostics.
3. One advanced real-tool demo passes nightly with bounded flake.

## 9. Test Matrix for Implementation

### 9.1 Unit tests
- Schema validation for new fields and illegal combinations.
- Wait engine timing and priority ordering.
- Adapter guard/normalization contracts.
- Key/hotkey normalization maps.

### 9.2 Integration tests
- Persistent PTY scenario flow on POSIX.
- Persistent PTY scenario flow on Windows (ConPTY backend).
- Failure bundle integrity with intentional step failures.

### 9.3 CI/Nightly
- CI (all OS): lint, typecheck, tests, portable mock autonomous smoke.
- Nightly (all OS): advanced real-tool autonomous stress suite.

## 10. Rollout Plan

1. Land backend abstractions and feature flags.
2. Enable interactive primitives behind opt-in runtime flag.
3. Run dual-path nightly and compare pass/fail diagnostics.
4. Flip default when SLOs hold for 2 consecutive weeks.
