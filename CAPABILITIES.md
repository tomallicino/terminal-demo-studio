# Capability Registry

Canonical, source-backed map of shipped behavior.

## CAP-STUDIO-001: `tds` command surface

- Behavior: exposes `render`, `run`, `validate`, `lint`, `new`, `init`, `doctor`, `debug`.
- Entry points: `terminal_demo_studio/cli.py`, `pyproject.toml` (`[project.scripts] tds`).
- Evidence: `tests/test_cli.py`.

## CAP-STUDIO-002: run mode aliases and normalization

- Behavior: supports canonical + friendly aliases (`scripted`, `interactive`, `visual`, `video`).
- Entry points: `terminal_demo_studio/cli.py` (`_RUN_MODE_ALIASES`, `_normalize_run_mode`).
- Evidence: `tests/test_cli.py`.

## CAP-STUDIO-003: screenplay schema + interpolation

- Behavior: validates screenplay YAML and resolves variables (including default `tmp_dir`).
- Entry points: `terminal_demo_studio/models.py`, `terminal_demo_studio/interpolate.py`.
- Evidence: `tests/test_models.py`, `tests/test_interpolate.py`.

## CAP-STUDIO-004: packaged template catalog

- Behavior: built-in templates are discoverable in source and installed contexts.
- Entry points: `terminal_demo_studio/resources.py`, `terminal_demo_studio/templates/*.yaml`.
- Evidence: `tests/test_cli.py::test_new_list_templates_returns_launch_pack_set`.

## CAP-STUDIO-005: workspace bootstrap

- Behavior: `tds init` creates workspace folders and starter screenplay with next-step guidance.
- Entry points: `terminal_demo_studio/cli.py` (`init`).
- Evidence: `tests/test_cli.py::test_init_creates_starter_workspace`.

## CAP-STUDIO-006: screenplay validation and explain output

- Behavior: `tds validate` supports schema output and explain-mode summary.
- Entry points: `terminal_demo_studio/cli.py` (`validate`).
- Evidence: `tests/test_cli.py`.

## CAP-STUDIO-007: static linting for autonomous policy safety

- Behavior: `tds lint` checks prompt policies and unsupported autonomous-video actions without execution.
- Entry points: `terminal_demo_studio/linting.py`, `terminal_demo_studio/prompt_policy.py`.
- Evidence: `tests/test_cli.py::test_lint_json_outputs_machine_readable_payload`.

## CAP-STUDIO-008: scripted tape compiler

- Behavior: compiles screenplay actions into VHS commands, waits, prompt setup, and key events.
- Entry points: `terminal_demo_studio/tape.py`.
- Evidence: `tests/test_tape.py`, `tests/test_smoke_compile.py`.

## CAP-STUDIO-009: scripted rendering lane (`scripted_vhs`)

- Behavior: executes preinstall/setup, renders scene media, and composes final outputs.
- Entry points: `terminal_demo_studio/director.py`, `terminal_demo_studio/editor.py`.
- Evidence: `tests/test_director.py`, `tests/test_editor.py`.

## CAP-STUDIO-010: split-screen playback control

- Behavior: supports sequential and simultaneous playback across multiple scenarios.
- Entry points: `terminal_demo_studio/editor.py` (`_timeline_offsets`).
- Evidence: `tests/test_editor.py`.

## CAP-STUDIO-011: label rendering fallback chain

- Behavior: drawtext-first with Pillow image-overlay fallback; avoids blank header when labels cannot render.
- Entry points: `terminal_demo_studio/editor.py` (`_resolve_label_renderer`, `_resolve_header_mode`).
- Evidence: `tests/test_editor.py`.

## CAP-STUDIO-012: autonomous command/assert lane (`autonomous_pty`)

- Behavior: executes command workflows with waits/assertions and event logging.
- Entry points: `terminal_demo_studio/runtime/runner.py`.
- Evidence: `tests/test_runtime_runner.py`, `tests/test_runtime_waits.py`.

## CAP-STUDIO-013: interactive guardrail in `autonomous_pty`

- Behavior: explicit failure when `input`/`key`/`hotkey` is used in PTY lane.
- Entry points: `terminal_demo_studio/runtime/runner.py` (`_unsupported_interactive_reason`).
- Evidence: `tests/test_runtime_runner.py::test_autonomous_runner_fails_on_interactive_key_action`.

## CAP-STUDIO-014: autonomous visual lane (`autonomous_video`)

- Behavior: full-screen terminal capture with keyboard/text actions, waits/assertions, and composed media outputs.
- Entry points: `terminal_demo_studio/runtime/video_runner.py`.
- Evidence: `tests/test_runtime_video_runner.py`.

## CAP-STUDIO-015: prompt-loop policy controls

- Behavior: supports `manual`, `approve`, and `deny` modes with regex gating and bounded rounds.
- Entry points: `terminal_demo_studio/models.py` (`AgentPromptPolicy`), `terminal_demo_studio/prompt_policy.py`, `terminal_demo_studio/runtime/video_runner.py`.
- Evidence: `tests/test_runtime_video_runner.py`.

## CAP-STUDIO-016: command-prefix allowlisting for approvals

- Behavior: optional `allowed_command_prefixes` restricts what approve mode can confirm.
- Entry points: `terminal_demo_studio/models.py`, `terminal_demo_studio/runtime/video_runner.py`.
- Evidence: `tests/test_runtime_video_runner.py`.

## CAP-STUDIO-017: media redaction + failure redaction

- Behavior: media masking modes plus sensitive-value redaction in failure bundles.
- Entry points: `terminal_demo_studio/redaction.py`, `terminal_demo_studio/runtime/video_runner.py`.
- Evidence: `tests/test_runtime_video_runner.py::test_video_runner_redacts_sensitive_values_in_failure_bundle`.

## CAP-STUDIO-018: canonical artifact layout

- Behavior: stable manifest/summary/media/runtime/failure structure across lanes.
- Entry points: `terminal_demo_studio/artifacts.py`.
- Evidence: `tests/test_director.py::test_run_director_writes_canonical_artifact_layout`.

## CAP-STUDIO-019: machine-readable CLI output contract

- Behavior: emits `STATUS`, `RUN_DIR`, `MEDIA_*`, `SUMMARY`, `EVENTS` for automation consumers.
- Entry points: `terminal_demo_studio/cli.py` (`_emit_result`).
- Evidence: `tests/test_cli.py`.

## CAP-STUDIO-020: Docker execution + fallback policy

- Behavior: strict `--docker`, strict `--local`, and lane-aware auto fallback behavior.
- Entry points: `terminal_demo_studio/cli.py` (`_execute_render`), `terminal_demo_studio/docker_runner.py`.
- Evidence: `tests/test_cli.py::test_run_auto_falls_back_to_local_when_docker_unavailable`, `tests/test_docker_runner.py`.

## CAP-STUDIO-021: doctor diagnostics with remediation hints

- Behavior: mode-aware dependency checks with actionable `NEXT:` suggestions.
- Entry points: `terminal_demo_studio/doctor.py`, `terminal_demo_studio/cli.py` (`doctor`).
- Evidence: `tests/test_doctor.py`, `tests/test_doctor_local_checks.py`.

## CAP-STUDIO-022: reusable GitHub render action

- Behavior: composite action renders screenplay, emits outputs, uploads artifacts, and can comment on PRs.
- Entry points: `.github/actions/render/action.yml`.
- Evidence: `.github/workflows/ci.yml` (`Composite action smoke`).

## CAP-STUDIO-023: release and smoke gate scripts

- Behavior: README/install-context/release preflight checks are automated.
- Entry points: `scripts/readme_smoke.sh`, `scripts/install_context_smoke.sh`, `scripts/release_preflight.sh`.
- Evidence: `.github/workflows/ci.yml`.

## CAP-STUDIO-024: deterministic showcase media pipeline

- Behavior: curated multi-theme/media showcase screenplays are batch-renderable to docs assets.
- Entry points: `examples/showcase/*.yaml`, `scripts/render_showcase_media.sh`.
- Evidence: `docs/media/*.gif`, `docs/media/*.mp4`.
