# Capability Registry

Canonical list of implemented capabilities in this repository.

## CAP-STUDIO-001: CLI Orchestration
- Behavior: Provides `studio` subcommands for `run`, `validate`, `new`, and `doctor`.
- Entry points:
  - `terminal_demo_studio/cli.py` -> `app`, `run`, `validate`, `new`, `doctor`
  - `pyproject.toml` -> `[project.scripts] studio`
- Evidence:
  - `tests/test_cli.py`

## CAP-STUDIO-002: Screenplay Schema v2 + Legacy Compatibility
- Behavior: Validates screenplay schema with both legacy (`type/wait_for`) and v2 action fields (`command`, `key`, `hotkey`, assertions/waits, execution mode, shell, adapter).
- Entry points:
  - `terminal_demo_studio/models.py` -> `Action`, `Scenario`, `Screenplay`, `parse_screenplay_data`
- Evidence:
  - `tests/test_models.py`

## CAP-STUDIO-003: Built-in Variable Interpolation
- Behavior: Supports interpolation and injects `tmp_dir` default for portable templates.
- Entry points:
  - `terminal_demo_studio/models.py` -> `parse_screenplay_data`
  - `terminal_demo_studio/interpolate.py` -> `interpolate_variables`
- Evidence:
  - `tests/test_interpolate.py`

## CAP-STUDIO-004: Scripted VHS Compilation
- Behavior: Compiles deterministic tapes including command/key/hotkey and wait/assert mappings.
- Entry points:
  - `terminal_demo_studio/tape.py` -> `compile_tape`
- Evidence:
  - `tests/test_tape.py`
  - `tests/test_smoke_compile.py`

## CAP-STUDIO-005: Scripted Render Director
- Behavior: Executes preinstall through cross-platform shell launcher and renders scenario outputs.
- Entry points:
  - `terminal_demo_studio/director.py` -> `run_director`, `_build_shell_command`
- Evidence:
  - `tests/test_director.py`

## CAP-STUDIO-006: Autonomous Runtime Lane
- Behavior: Executes command/assert scenarios in closed loop, evaluates waits/assertions, and writes event/summary/failure artifacts.
- Entry points:
  - `terminal_demo_studio/runtime/runner.py` -> `run_autonomous_screenplay`
  - `terminal_demo_studio/runtime/waits.py` -> `evaluate_wait_condition`
- Evidence:
  - `tests/test_runtime_runner.py`
  - `tests/test_runtime_waits.py`

## CAP-STUDIO-007: Adapter Abstraction
- Behavior: Provides adapter selection for normalization and future tool-specific policies.
- Entry points:
  - `terminal_demo_studio/adapters/base.py` -> `RuntimeAdapter`, `get_adapter`
- Evidence:
  - `terminal_demo_studio/adapters/base.py`

## CAP-STUDIO-008: Docker Rendering Path
- Behavior: Builds/reuses image and runs rendering inside container when requested.
- Entry points:
  - `terminal_demo_studio/docker_runner.py` -> `compute_image_tag`, `ensure_image`, `run_in_docker`
  - `Dockerfile`
- Evidence:
  - `tests/test_docker_runner.py`

## CAP-STUDIO-009: Auto Docker Fallback + Strict Explicit Docker
- Behavior: Default `studio run` attempts Docker then falls back to local; explicit `--docker` remains strict.
- Entry points:
  - `terminal_demo_studio/cli.py` -> `run`
- Evidence:
  - `tests/test_cli.py::test_run_auto_falls_back_to_local_when_docker_unavailable`
  - `tests/test_cli.py::test_run_explicit_docker_stays_strict_when_docker_unavailable`

## CAP-STUDIO-010: Packaged Template Discovery
- Behavior: Lists and loads packaged templates in installed contexts.
- Entry points:
  - `terminal_demo_studio/resources.py` -> `list_template_names`, `read_template`
  - `terminal_demo_studio/cli.py` -> `new`
- Evidence:
  - `tests/test_cli.py::test_new_list_templates_ignores_module_file_location`

## CAP-STUDIO-011: Mode-Aware Doctor Checks
- Behavior: Performs local binary/drawtext checks, template validation, and optional Docker diagnostics.
- Entry points:
  - `terminal_demo_studio/doctor.py` -> `run_doctor_checks`
  - `terminal_demo_studio/cli.py` -> `doctor`
- Evidence:
  - `tests/test_doctor.py`
  - `tests/test_doctor_local_checks.py`

## CAP-STUDIO-012: Portable-First Demo Catalog
- Behavior: Ships portable mock complex-TUI examples by default and advanced real-tool examples separately.
- Entry points:
  - `examples/mock/`
  - `examples/real/`
  - `README.md`
- Evidence:
  - `examples/mock/safety_wizard.yaml`
  - `examples/real/real_agent_demo.manifest.yaml`

## CAP-STUDIO-013: Release Safety and Smoke Gates
- Behavior: Enforces preflight checks, README smoke, and install-context smoke.
- Entry points:
  - `scripts/release_preflight.sh`
  - `scripts/readme_smoke.sh`
  - `scripts/install_context_smoke.sh`
- Evidence:
  - `.github/workflows/ci.yml`

## CAP-STUDIO-014: Autonomous Interactive Guardrail
- Behavior: Prevents silent no-op behavior by failing autonomous runs when interactive input primitives (`input`, `key`, `hotkey`) are used.
- Entry points:
  - `terminal_demo_studio/runtime/runner.py` -> `_unsupported_interactive_reason`, `run_autonomous_screenplay`
- Evidence:
  - `tests/test_runtime_runner.py::test_autonomous_runner_fails_on_interactive_key_action`

## CAP-STUDIO-015: Workspace Bootstrap (`studio init`)
- Behavior: Creates plug-and-play workspace directories and scaffolds a starter screenplay template for first-run users/agents.
- Entry points:
  - `terminal_demo_studio/cli.py` -> `init`, `_write_screenplay_from_template`
- Evidence:
  - `tests/test_cli.py::test_init_creates_starter_workspace`
  - `tests/test_cli.py::test_init_respects_existing_file_without_force`

## CAP-STUDIO-016: Headerless Composition Fallback
- Behavior: Avoids blank top bars by disabling header inset/styling when labels are not renderable (no drawtext or no labels).
- Entry points:
  - `terminal_demo_studio/editor.py` -> `_resolve_header_mode`, `_build_filter_complex`, `compose_split_screen`
- Evidence:
  - `tests/test_editor.py::test_compose_skips_header_when_drawtext_is_unavailable`
  - `tests/test_editor.py::test_compose_skips_header_when_labels_are_empty`
