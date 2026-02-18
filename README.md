# terminal-demo-studio

Deterministic terminal/TUI demo automation for docs, launches, and agent workflows.

All showcase media is generated from executed sessions (mock or real). No hand-edited frames.

![Hero demo: bugfix before/after](docs/media/hero-bugfix-sequential.gif)

## Agent Automation First

Install the skill:

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

Agent-first default flow:

```bash
studio new demo_name --template mock_wizard --destination screenplays
studio validate screenplays/demo_name.yaml --explain
studio run screenplays/demo_name.yaml --mode scripted_vhs --local --output-dir outputs
```

Example agent prompt:

```text
Create a portable mock workflow demo, validate it, render a GIF locally, and return the output path.
```

## 60-Second Quickstart (Local First)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

studio doctor --mode auto
studio validate examples/mock/safety_wizard.yaml --explain
studio run examples/mock/safety_wizard.yaml --mode scripted_vhs --local --output-dir outputs --no-mp4
```

Core workflows do not require Docker.

## Compatibility Matrix (v1)

| Platform | `scripted_vhs` lane | `autonomous_pty` lane | Docker |
| --- | --- | --- | --- |
| macOS | CI-verified render | CI-verified smoke | Optional |
| Linux | CI-verified render | CI-verified smoke | Optional |
| Windows 10/11 (native) | Not CI-rendered yet (use WSL2 if needed today) | CI-verified smoke (command/assert flows) | Optional |

Important: `autonomous_pty` currently supports command/assert-style autonomous flows. Interactive key-driven autonomy is planned, not release-complete.

## Demo Showcase (Portable-First)

1. Hero before/after bugfix flow (Catppuccin Mocha)
Source screenplay: `screenplays/dev_bugfix_workflow.yaml`
![Hero bugfix demo](docs/media/hero-bugfix-sequential.gif)

2. Simultaneous playback mode comparison (GruvboxDark)
Source screenplay: `screenplays/agent_generated_release_check.yaml`
![Playback simultaneous demo](docs/media/playback-simultaneous.gif)

3. Single-pane macOS prompt style (Dracula)
Source screenplay: `screenplays/single_prompt_macos_demo.yaml`
![macOS prompt demo](docs/media/macos-prompt-single-pane.gif)

4. Feature-flag workflow before/after (Nord)
Source screenplay: `screenplays/agent_generated_feature_flag_fix.yaml`
![Feature flag demo](docs/media/feature-flag-bugfix.gif)

## Complex TUI Automation Modes

- `scripted_vhs`: deterministic cinematic output (best default for README/public showcases).
- `autonomous_pty`: closed-loop command/assert execution with event logs and failure bundles.

Portable mock demos are the default public examples for reliability and cross-platform reproducibility.
Advanced real-tool demos are available in `examples/real/` and require stricter setup/verification.

## Command Reference

```bash
studio run <screenplay.yaml> [--mode auto|scripted_vhs|autonomous_pty] \
  [--docker|--local] [--output-dir PATH] [--keep-temp] [--rebuild] \
  [--playback sequential|simultaneous] [--no-mp4] [--no-gif]

studio validate <screenplay.yaml> [--json-schema] [--explain]
studio new <name> [--template TEMPLATE] [--destination PATH] [--force]
studio new --list-templates
studio doctor [--mode auto|scripted_vhs|autonomous_pty]
```

## Autonomous Status and Roadmap

What is reliable today:

- Command/assert automation (`command`, waits, regex assertions, exit checks).
- Run artifacts: `events.jsonl`, `summary.json`, and `failure/` bundle on failure.

What is not yet release-complete:

- True interactive key/hotkey/input automation in `autonomous_pty` for complex live TUIs.

Roadmap: `docs/autonomous-roadmap.md`

## Skill and Packaging

- Skill file: `skills/terminal-demo-studio/SKILL.md`
- PyPI distribution: `terminal-demo-studio-cli`
- Python package: `terminal_demo_studio`
- CLI command: `studio`
- Product + skill ship in one repo (no separate skill repo needed).

## Docs

- `ARCHITECTURE.md`
- `CAPABILITIES.md`
- `docs/case-studies/feature-flag-bugfix.md`
- `docs/releasing.md`

## License

MIT (`LICENSE`)
