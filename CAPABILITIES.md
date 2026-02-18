# Capability Registry

Canonical map of shipped behavior in this repository.

## CAP-STUDIO-001: `tds` CLI Command Surface
- Behavior: Exposes `render`, `run`, `validate`, `new`, `init`, `doctor`, and `debug` commands.
- Entry points:
  - `terminal_demo_studio/cli.py`
  - `pyproject.toml` (`[project.scripts] tds`)
- Evidence:
  - `tests/test_cli.py`

## CAP-STUDIO-002: Screenplay Schema + Variable Interpolation
- Behavior: Validates screenplay YAML (legacy + v2 action fields) and interpolates variables including default `tmp_dir`.
- Entry points:
  - `terminal_demo_studio/models.py` (`Action`, `Scenario`, `Screenplay`, `parse_screenplay_data`)
  - `terminal_demo_studio/interpolate.py`
- Evidence:
  - `tests/test_models.py`
  - `tests/test_interpolate.py`

## CAP-STUDIO-003: Packaged Template Discovery
- Behavior: Lists/loads built-in templates from package resources in source and installed contexts.
- Entry points:
  - `terminal_demo_studio/resources.py` (`list_template_names`, `read_template`)
- Evidence:
  - `tests/test_cli.py::test_new_list_templates_ignores_module_file_location`

## CAP-STUDIO-004: Golden Template Catalog (6 launch templates)
- Behavior: Ships six launch templates for plug-and-play onboarding and gallery demos.
- Entry points:
  - `terminal_demo_studio/templates/install_first_command.yaml`
  - `terminal_demo_studio/templates/before_after_bugfix.yaml`
  - `terminal_demo_studio/templates/error_then_fix.yaml`
  - `terminal_demo_studio/templates/interactive_menu_showcase.yaml`
  - `terminal_demo_studio/templates/policy_warning_gate.yaml`
  - `terminal_demo_studio/templates/speedrun_cuts.yaml`
- Evidence:
  - `tests/test_cli.py::test_new_list_templates_returns_launch_pack_set`

## CAP-STUDIO-005: Scripted Tape Compiler
- Behavior: Compiles screenplay actions into VHS directives (commands, waits, assertions, key/hotkey, prompt setup).
- Entry points:
  - `terminal_demo_studio/tape.py` (`compile_tape`)
- Evidence:
  - `tests/test_tape.py`
  - `tests/test_smoke_compile.py`

## CAP-STUDIO-006: Scripted VHS Lane (`scripted_vhs`)
- Behavior: Runs preinstall/setup, renders scenario videos, and composes final media assets.
- Entry points:
  - `terminal_demo_studio/director.py` (`run_director`)
  - `terminal_demo_studio/editor.py` (`compose_split_screen`)
- Evidence:
  - `tests/test_director.py`
  - `tests/test_editor.py`

## CAP-STUDIO-007: Autonomous PTY Lane (`autonomous_pty`)
- Behavior: Executes command/assert workflows, evaluates waits/assertions, and writes runtime/failure artifacts.
- Entry points:
  - `terminal_demo_studio/runtime/runner.py` (`run_autonomous_screenplay`)
  - `terminal_demo_studio/runtime/waits.py`
- Evidence:
  - `tests/test_runtime_runner.py`
  - `tests/test_runtime_waits.py`

## CAP-STUDIO-008: Autonomous PTY Interactive Guardrail
- Behavior: Fails fast (with explicit reason) when unsupported `input`/`key`/`hotkey` actions are used in `autonomous_pty`.
- Entry points:
  - `terminal_demo_studio/runtime/runner.py` (`_unsupported_interactive_reason`)
- Evidence:
  - `tests/test_runtime_runner.py::test_autonomous_runner_fails_on_interactive_key_action`

## CAP-STUDIO-009: Autonomous Video Lane (`autonomous_video`) (experimental)
- Behavior: Captures interactive terminal UI sessions via virtual display + kitty remote control + ffmpeg.
- Entry points:
  - `terminal_demo_studio/runtime/video_runner.py` (`run_autonomous_video_screenplay`)
- Evidence:
  - `tests/test_runtime_video_runner.py`

## CAP-STUDIO-010: Canonical Run Artifact Layout
- Behavior: Creates stable run directories and writes shared manifests/summaries across all lanes.
- Entry points:
  - `terminal_demo_studio/artifacts.py` (`create_run_layout`, `write_manifest`, `write_summary`)
- Evidence:
  - `tests/test_director.py::test_run_director_writes_canonical_artifact_layout`
  - `tests/test_runtime_runner.py::test_autonomous_runner_writes_event_log_and_summary`

## CAP-STUDIO-011: Machine-Friendly Run Output Contract
- Behavior: Emits `STATUS=`, `RUN_DIR=`, `MEDIA_*=` and `SUMMARY=/EVENTS=` for automation consumers.
- Entry points:
  - `terminal_demo_studio/cli.py` (`_emit_result`, `render`, `run`)
- Evidence:
  - `tests/test_cli.py::test_render_local_dispatches_to_director`
  - `tests/test_cli.py::test_run_autonomous_mode_invokes_autonomous_runner`

## CAP-STUDIO-012: Debug Command for Triage
- Behavior: `tds debug` provides compact human summary and JSON mode (`--json`) for agents.
- Entry points:
  - `terminal_demo_studio/cli.py` (`debug`)
- Evidence:
  - `tests/test_cli.py::test_debug_outputs_compact_summary`
  - `tests/test_cli.py::test_debug_json_outputs_machine_readable_payload`

## CAP-STUDIO-013: Docker Execution + Mode-Aware Fallback
- Behavior:
  - Explicit `--docker` remains strict.
  - `scripted_vhs` auto path can fallback to local when Docker is unavailable.
  - `autonomous_video` auto path prefers local then Docker fallback.
  - `autonomous_pty` stays local.
- Entry points:
  - `terminal_demo_studio/cli.py` (`_execute_render`)
  - `terminal_demo_studio/docker_runner.py` (`run_in_docker`)
- Evidence:
  - `tests/test_cli.py::test_run_auto_falls_back_to_local_when_docker_unavailable`
  - `tests/test_cli.py::test_run_explicit_docker_stays_strict_when_docker_unavailable`
  - `tests/test_docker_runner.py`

## CAP-STUDIO-014: Mode-Aware Doctor Diagnostics
- Behavior: Reports dependency readiness with concise per-check remediation (`NEXT:` command).
- Entry points:
  - `terminal_demo_studio/doctor.py` (`run_doctor_checks`)
  - `terminal_demo_studio/cli.py` (`doctor`)
- Evidence:
  - `tests/test_doctor.py`
  - `tests/test_doctor_local_checks.py`

## CAP-STUDIO-015: Workspace Bootstrap (`tds init`)
- Behavior: Creates plug-and-play workspace directories and starter screenplay with immediate next steps.
- Entry points:
  - `terminal_demo_studio/cli.py` (`init`)
- Evidence:
  - `tests/test_cli.py::test_init_creates_starter_workspace`

## CAP-STUDIO-016: Label Rendering Fallback Behavior
- Behavior: Uses drawtext when available, image-overlay fallback when not, and avoids blank header bands when labels are not renderable.
- Entry points:
  - `terminal_demo_studio/editor.py` (`_resolve_label_renderer`, `_resolve_header_mode`, `compose_split_screen`)
- Evidence:
  - `tests/test_editor.py`

## CAP-STUDIO-017: Reusable GitHub Render Action
- Behavior: Composite action renders a screenplay, emits run outputs, uploads artifacts, and can post PR comments.
- Entry points:
  - `.github/actions/render/action.yml`
  - `docs/github-action.md`
- Evidence:
  - `.github/workflows/ci.yml` (`Composite action smoke`)

## CAP-STUDIO-018: Release/Privacy Safety Gates
- Behavior: Enforces preflight checks and smoke scripts for README/install-context correctness.
- Entry points:
  - `scripts/release_preflight.sh`
  - `scripts/readme_smoke.sh`
  - `scripts/install_context_smoke.sh`
- Evidence:
  - `.github/workflows/ci.yml`

## CAP-STUDIO-019: Deterministic Autonomous Video Mock Fixtures
- Behavior: Provides deterministic interactive mock fixtures and screenplays for `autonomous_video` smoke coverage.
- Entry points:
  - `fixtures/autonomous_video/mock_codex_like_tui.py`
  - `fixtures/autonomous_video/mock_claude_like_tui.py`
  - `examples/mock/autonomous_video_codex_like.yaml`
  - `examples/mock/autonomous_video_claude_like.yaml`
- Evidence:
  - `tests/test_runtime_video_runner.py`
