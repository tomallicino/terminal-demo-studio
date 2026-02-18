# terminal-demo-studio

[![PyPI](https://img.shields.io/pypi/v/terminal-demo-studio)](https://pypi.org/project/terminal-demo-studio/)
[![GitHub stars](https://img.shields.io/github/stars/tomallicino/terminal-demo-studio?style=social)](https://github.com/tomallicino/terminal-demo-studio/stargazers)
[![License](https://img.shields.io/github/license/tomallicino/terminal-demo-studio)](LICENSE)

**Built for the agent era.**

Deterministic terminal/TUI demos for docs, launches, and CI. Render polished MP4/GIF assets from executed sessions, not hand-edited frames.

Built on [Charm VHS](https://github.com/charmbracelet/vhs), with autonomous runtime lanes, safety gates, and machine-readable artifacts.

![Install and first command](docs/media/install_first_command.gif)

## Why Teams Use It

- **Deterministic outputs:** same screenplay, same artifact contract.
- **Real execution:** demos come from actual command/TUI runs.
- **Agent-native:** structured outputs (`STATUS`, `RUN_DIR`, `MEDIA_*`, `EVENTS`, `SUMMARY`) and JSON debug/lint modes.
- **Safer autonomy:** bounded prompt loops, allowlist options, preflight lint, redaction pipeline.

## Execution Lanes

- `scripted` (`scripted_vhs`): high-fidelity tape rendering for repeatable marketing/docs demos.
- `interactive` (`autonomous_pty`): command/assert automation for deterministic CLI workflows.
- `visual` (`autonomous_video`): full-screen complex TUI capture with programmable keys/text and screen-gated waits.

## 60-Second Quickstart

```bash
pipx install terminal-demo-studio
tds render --template install_first_command --output gif --output-dir outputs
```

Migration note: the `studio` command was removed in alpha. Use `tds`.

## Agent Workflow (Plug-and-Play)

Install the skill:

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

Agent prompt example:

```text
Render a visual demo from examples/real/autonomous_video_codex_multiturn.yaml, return RUN_DIR and MEDIA_MP4, then summarize any issues from tds debug --json.
```

## Pause Before Sending Input

Yes. This is supported today and works well for “show the prompt, then send” flows.

Use `input` to type without submit, then `sleep`, then press `enter`:

```yaml
actions:
  - input: "Create a hello world project with Python and explain each file"
    sleep: 1200ms
  - key: enter
  - wait_for: "Working"
    wait_mode: screen
    wait_timeout: 20s
```

This pattern is especially useful for autonomous_video demos where you want viewers to see intent before execution.

## Command Cheatsheet

```bash
tds render <screenplay.yaml> [--mode auto|scripted|interactive|visual] \
  [--docker|--local] [--output-dir PATH] [--playback sequential|simultaneous] \
  [--output gif|mp4] [--agent-prompts auto|manual|approve|deny] \
  [--redact auto|off|input_line]

tds run <screenplay.yaml> [same options as render]
tds validate <screenplay.yaml> [--json-schema] [--explain]
tds lint <screenplay.yaml> [--json] [--strict]
tds new <name> [--template TEMPLATE] [--destination PATH] [--force]
tds new --list-templates
tds init [--destination PATH] [--template TEMPLATE] [--name NAME] [--force]
tds doctor [--mode auto|scripted|interactive|visual]
tds debug <run_dir> [--json]
```

## Safety + Reliability

### Prompt loops (`autonomous_video`)

- `--agent-prompts manual`: no automatic approve/deny.
- `--agent-prompts approve`: automated approval when prompt regex matches.
- `--agent-prompts deny`: automated denial when prompt regex matches.
- `--agent-prompts auto`: use screenplay/scenario policy.

Safety guards:

- `tds lint` validates policy/action safety before execution.
- Approve mode requires scoped `allow_regex`.
- Trivially unbounded approve patterns (like `.*`) are blocked by default.
- Optional `allowed_command_prefixes` can scope what approvals are allowed to confirm.
- Manual-mode prompt blocks fail fast with actionable diagnostics.

### Redaction

- `--redact auto` (default): detects sensitive actions and enables input-line masking when needed.
- `--redact input_line`: always mask the input line region in output media.
- `--redact off`: disable media masking.

Failure bundle text is value-redacted by default for token/API-key-like patterns.

### Container hardening knobs

- `TDS_DOCKER_HARDENING=1` (default): `no-new-privileges`, dropped caps, PID limit.
- `TDS_DOCKER_PIDS_LIMIT=512` (default).
- `TDS_DOCKER_NETWORK` (optional, e.g. `none`).
- `TDS_DOCKER_READ_ONLY=1` (optional).
- `TDS_DOCKER_VERBOSE=1` (optional log streaming).

## Real Codex Workflows

Screenplays using real Codex CLI:

- `examples/real/autonomous_video_codex_cli.yaml`
- `examples/real/autonomous_video_codex_multiturn.yaml`
- `examples/real/autonomous_video_codex_patch_flow.yaml`
- `examples/real/autonomous_video_codex_complex_verified.yaml`
- `examples/real/autonomous_video_codex_hello_project_approval.yaml`
- `examples/real/autonomous_video_codex_hello_project_deny.yaml`

Run one:

```bash
tds run examples/real/autonomous_video_codex_hello_project_approval.yaml \
  --mode visual --output mp4 --redact input_line
```

## Artifact Contract

Every run writes `.terminal_demo_studio_runs/<run-id>/` with:

- `manifest.json`
- `summary.json`
- `media/*.mp4|*.gif`
- `runtime/events.jsonl` (autonomous lanes)
- `failure/*` on errors

Machine-friendly stdout keys:

- `STATUS`
- `RUN_DIR`
- `MEDIA_MP4` / `MEDIA_GIF`
- `EVENTS`
- `SUMMARY`

## Compatibility

| Platform | `scripted_vhs` | `autonomous_pty` | `autonomous_video` | Docker |
| --- | --- | --- | --- | --- |
| macOS | Supported | Supported | Experimental | Optional |
| Linux | Supported | Supported | Experimental | Optional |
| Windows | Supported | Supported | Docker-first | Optional |

## Troubleshooting

```bash
tds doctor --mode visual
tds debug <run_dir>
tds debug <run_dir> --json
```

## Additional Docs

- `ARCHITECTURE.md`
- `CAPABILITIES.md`
- `docs/autonomous-roadmap.md`
- `docs/github-action.md`
- `docs/reproducibility.md`
- `docs/releasing.md`

## License

MIT (`LICENSE`)
