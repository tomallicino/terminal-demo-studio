# terminal-demo-studio

[![PyPI](https://img.shields.io/pypi/v/terminal-demo-studio?color=2E8555)](https://pypi.org/project/terminal-demo-studio/)
[![Python](https://img.shields.io/pypi/pyversions/terminal-demo-studio)](https://pypi.org/project/terminal-demo-studio/)
[![CI](https://img.shields.io/github/actions/workflow/status/tomallicino/terminal-demo-studio/ci.yml?label=ci)](https://github.com/tomallicino/terminal-demo-studio/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/tomallicino/terminal-demo-studio)](LICENSE)

**Turn YAML screenplays into deterministic GIF/MP4 terminal demos.** Capture any TUI &mdash; Claude Code, Codex, htop, vim &mdash; with full keyboard interaction, approval-prompt automation, and safety controls.

![Onboarding Neon](docs/media/onboarding_tokyo_neon.gif)

---

## What it does

- **YAML in, GIF/MP4 out.** Define a screenplay, get a repeatable demo video. No screen recording by hand.
- **Three execution lanes.** Polished scripted renders, command/assert automation, or full-screen TUI capture with live keyboard interaction.
- **Captures complex TUIs.** Claude Code, Codex, htop, vim, any interactive terminal app &mdash; rendered through a real terminal emulator (Kitty), not a text-mode simulator.
- **Agent-native.** Machine-readable output contract (`STATUS`, `RUN_DIR`, `MEDIA_GIF`, `SUMMARY`, `EVENTS`) that agents can parse and act on.
- **Safe by default.** Prompt-loop policies, lint gates, media redaction, bounded waits, and failure bundles with redacted diagnostics.

---

## Quickstart

```bash
pip install terminal-demo-studio
tds init --destination my_demo
tds render my_demo/screenplays/getting_started.yaml --mode scripted --local --output gif --output-dir my_demo/outputs
```

That's it. Your GIF is in `my_demo/outputs/`.

### Using Docker (zero local dependencies)

```bash
tds render my_demo/screenplays/getting_started.yaml --docker --output gif --output-dir my_demo/outputs
```

Docker mode bundles all system dependencies (vhs, ffmpeg, kitty, xvfb) automatically.

---

## Platform support

| | Windows | macOS | Linux |
|---|:---:|:---:|:---:|
| **Scripted** (`--mode scripted`) | Docker or local (vhs + ffmpeg) | Local or Docker | Local or Docker |
| **Interactive** (`--mode interactive`) | Local | Local | Local |
| **Visual** (`--mode visual`) | Docker | Docker or local (kitty + xvfb) | Local or Docker |
| **`pip install`** | Yes | Yes | Yes |
| **Python 3.11+** | Yes | Yes | Yes |

`tds render` auto-selects Docker when local dependencies are missing. Use `--local` to force local mode or `--docker` to force Docker mode.

---

## Three execution lanes

### Scripted (`--mode scripted`)

Cinematic, deterministic renders for marketing and docs. Compiles YAML actions into [VHS](https://github.com/charmbracelet/vhs) tape format, renders through a headless terminal, and produces pixel-perfect GIF/MP4.

```bash
tds render screenplay.yaml --mode scripted --output gif
```

### Interactive (`--mode interactive`)

Command/assert automation. Runs commands via subprocess, evaluates wait conditions and assertions, logs runtime events. No video output &mdash; pure execution verification.

```bash
tds run screenplay.yaml --mode interactive --output-dir outputs
```

### Visual (`--mode visual`)

Full-screen TUI capture. Launches a Kitty terminal on a virtual X display, sends keystrokes, captures video with FFmpeg. Handles approval prompts automatically via configurable policies.

```bash
tds run screenplay.yaml --mode visual --output mp4
```

---

## Capturing complex TUIs

The visual lane can capture any interactive terminal application. Here are real demos generated from YAML screenplays:

### Claude Code (autonomous_video)

Captures a real Claude Code session &mdash; onboarding flow, interactive prompts, and all.

![Claude Code Demo](docs/media/autonomous_claude_real_short.gif)

[GIF](docs/media/autonomous_claude_real_short.gif) &middot; [MP4](docs/media/autonomous_claude_real_short.mp4) &middot; [YAML](examples/showcase/autonomous_claude_real_short.yaml)

### Codex (autonomous_video)

Builds and verifies a hello-world app through the Codex TUI.

![Codex Demo](docs/media/autonomous_codex_real_short.gif)

[GIF](docs/media/autonomous_codex_real_short.gif) &middot; [MP4](docs/media/autonomous_codex_real_short.mp4) &middot; [YAML](examples/showcase/autonomous_codex_real_short.yaml)

---

## Showcase gallery

All scripted demos below were generated from YAML screenplays in this repo.

| Demo | Theme | Preview |
|------|-------|---------|
| [Onboarding Neon](examples/showcase/onboarding_tokyo_neon.yaml) | TokyoNightStorm | ![](docs/media/onboarding_tokyo_neon.gif) |
| [Bugfix Glow](examples/showcase/bugfix_catppuccin_glow.yaml) | Catppuccin Mocha | ![](docs/media/bugfix_catppuccin_glow.gif) |
| [Recovery Retro](examples/showcase/recovery_gruvbox_retro.yaml) | GruvboxDark | ![](docs/media/recovery_gruvbox_retro.gif) |
| [Policy Guard](examples/showcase/policy_nord_guard.yaml) | Nord | ![](docs/media/policy_nord_guard.gif) |
| [Menu Contrast](examples/showcase/menu_dracula_contrast.yaml) | Dracula | ![](docs/media/menu_dracula_contrast.gif) |
| [Nightshift Speedrun](examples/showcase/speedrun_nightshift.yaml) | TokyoNightStorm | ![](docs/media/speedrun_nightshift.gif) |

Regenerate all showcase media:

```bash
./scripts/render_showcase_media.sh
```

---

## Screenplay format

```yaml
title: "My Demo"
output: "my_demo"
settings:
  width: 1440
  height: 900
  theme: "TokyoNightStorm"
  font_family: "Menlo"
  framerate: 30
scenarios:
  - label: "Setup and run"
    execution_mode: "scripted_vhs"  # or autonomous_pty / autonomous_video
    setup:
      - "npm install"
    actions:
      - type: "npm start"
      - wait_for: "Server running"
        wait_mode: "screen"
        wait_timeout: "10s"
      - type: "curl localhost:3000"
      - wait_for: "Hello"
        wait_mode: "screen"
        wait_timeout: "5s"
```

### Action types

| Action | Lanes | Description |
|--------|-------|-------------|
| `type` / `command` | all | Type text (scripted) or execute command (autonomous) |
| `key` / `hotkey` | scripted, visual | Send a keystroke (`Enter`, `ctrl+c`, `Escape`) |
| `input` | visual | Type raw text without pressing Enter |
| `wait_for` | all | Wait for text to appear on screen |
| `wait_stable` / `sleep` | all | Pause for a duration |
| `assert_screen_regex` | interactive, visual | Assert screen content matches regex |
| `expect_exit_code` | interactive | Assert command exit code |

---

## CLI reference

```
tds render <screenplay.yaml>       Render a screenplay to GIF/MP4
    --mode auto|scripted|interactive|visual
    --docker | --local              Runtime location
    --output gif|mp4                Output format (repeat for both)
    --output-dir PATH               Output directory
    --playback sequential|simultaneous
    --agent-prompts auto|manual|approve|deny
    --redact auto|off|input_line
    --template TEMPLATE             Use built-in template instead of file
    --keep-temp                     Keep intermediate files

tds run <screenplay.yaml>          Alias for render (same options)

tds watch <screenplay.yaml>       Watch and auto-render on changes
    --mode auto|scripted|interactive|visual
    --docker | --local              Runtime location
    --output gif|mp4                Output format (repeat for both)
    --output-dir PATH               Output directory
    --debounce DURATION             Re-render debounce (default: 1000ms)

tds validate <screenplay.yaml>     Validate YAML schema
    --json-schema                   Print JSON schema
    --explain                       Show screenplay summary

tds lint <screenplay.yaml>         Lint for policy and safety issues
    --json                          JSON output
    --strict                        Treat warnings as errors

tds new <name>                     Create new screenplay from template
    --template TEMPLATE             Template name (default: before_after_bugfix)
    --list-templates                List available templates
    --destination PATH              Output directory

tds init                           Initialize workspace with starter screenplay
    --destination PATH              Workspace root (default: .)
    --template TEMPLATE             Starter template
    --name NAME                     Screenplay name

tds doctor                         Check dependency health
    --mode auto|scripted|interactive|visual

tds debug <run_dir>                Inspect a completed run
    --json                          JSON output
```

---

## Docker mode

Docker bundles all system dependencies (vhs, ffmpeg, kitty, xvfb, starship) in a single container image. The image is content-addressed and cached.

```bash
# Explicit Docker mode
tds render screenplay.yaml --docker --output gif

# Auto mode (uses Docker if available, falls back to local)
tds render screenplay.yaml --output gif

# Force rebuild the Docker image
tds render screenplay.yaml --docker --rebuild --output gif
```

Environment variables for Docker execution:

| Variable | Default | Description |
|----------|---------|-------------|
| `TDS_DOCKER_HARDENING` | `true` | Enable `--cap-drop ALL`, `--security-opt no-new-privileges` |
| `TDS_DOCKER_PIDS_LIMIT` | `512` | Container PID limit |
| `TDS_DOCKER_READ_ONLY` | `false` | Read-only root filesystem |
| `TDS_DOCKER_NETWORK` | (none) | Docker network mode |
| `TDS_DOCKER_IMAGE_RETENTION` | `3` | Number of cached images to keep |

---

## Safety and reliability

### Prompt policy

The visual lane can automatically handle approval prompts from AI agents (Claude Code, Codex):

```yaml
agent_prompts:
  mode: "approve"           # auto | manual | approve | deny
  prompt_regex: "(?i)(proceed|confirm|allow)"
  allow_regex: "safe operation"
  allowed_command_prefixes: ["npm", "git"]
  max_rounds: 5
  approve_key: "y"
  deny_key: "n"
```

### Lint gates

```bash
tds lint screenplay.yaml --strict
```

Catches unsafe configurations before execution: unbounded approval, missing prompt regex, unsupported actions per lane.

### Media redaction

```bash
tds render screenplay.yaml --redact auto
```

Modes: `auto` (redact detected secrets), `off`, `input_line` (mask typed input lines). Sensitive values from environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) are automatically detected and masked.

### Failure bundles

Failed runs produce a diagnostic bundle at `failure/`:
- `reason.txt` &mdash; redacted failure reason
- `screen.txt` &mdash; redacted terminal snapshot
- `step.json` &mdash; failed step metadata
- `video_runner.log` &mdash; redacted process logs

---

## GitHub Action

Add to your CI workflow:

```yaml
- uses: tomallicino/terminal-demo-studio/.github/actions/render@main
  with:
    screenplay: examples/showcase/onboarding_tokyo_neon.yaml
    mode: scripted_vhs
    outputs: gif
    output_dir: outputs
    upload_artifact: true
    comment_pr: true
```

See the [GitHub Action guide](docs/github-action.md) for full options.

---

## Agent integration

### MCP server (Claude Code, Cursor, Windsurf)

Install with MCP support and register the server:

```bash
pip install terminal-demo-studio[mcp]
```

Add to your project's `.mcp.json` (or configure via `claude mcp add`):

```json
{
  "mcpServers": {
    "terminal-demo-studio": {
      "type": "stdio",
      "command": "tds-mcp"
    }
  }
}
```

The MCP server exposes 6 tools: `tds_render`, `tds_validate`, `tds_lint`, `tds_debug`, `tds_list_templates`, `tds_doctor`. Agents can call these directly without shell parsing.

### Install as a skill

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

### Example agent prompt

```text
Render examples/showcase/policy_nord_guard.yaml in scripted mode.
Return STATUS, RUN_DIR, MEDIA_GIF, MEDIA_MP4, and SUMMARY.
If status is failed, run `tds debug <run_dir> --json` and summarize root cause.
```

### Output contract

Every `tds render` / `tds run` emits machine-readable keys:

```
STATUS=success
RUN_DIR=outputs/.terminal_demo_studio_runs/run-abc123
MEDIA_GIF=outputs/.terminal_demo_studio_runs/run-abc123/media/demo.gif
MEDIA_MP4=outputs/.terminal_demo_studio_runs/run-abc123/media/demo.mp4
SUMMARY=outputs/.terminal_demo_studio_runs/run-abc123/summary.json
EVENTS=outputs/.terminal_demo_studio_runs/run-abc123/runtime/events.jsonl
```

---

## Artifact contract

Each run writes `.terminal_demo_studio_runs/<run-id>/` with:

```
manifest.json           Run metadata
summary.json            Execution summary (status, lane, media paths)
media/*.gif|*.mp4       Rendered output
scenes/scene_*.mp4      Per-scenario videos (scripted, visual)
tapes/scene_*.tape      VHS tape files (scripted)
runtime/events.jsonl    Event log (autonomous lanes)
failure/*               Diagnostic bundle on failure
```

---

## Additional docs

- [Architecture](ARCHITECTURE.md)
- [Capability registry](CAPABILITIES.md)
- [Reproducibility](docs/reproducibility.md)
- [Autonomous roadmap](docs/autonomous-roadmap.md)
- [GitHub Action guide](docs/github-action.md)
- [Release checklist](docs/releasing.md)
- [Showcase gallery index](docs/showcase-gallery.md)

---

## License

MIT ([LICENSE](LICENSE))
