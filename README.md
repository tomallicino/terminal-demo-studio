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
- **Agent-native.** MCP server with 6 tools, machine-readable output contract, and a `tds watch` loop for live editing. Agents render, validate, lint, and debug without shell parsing.
- **Safe by default.** Prompt-loop policies, lint gates, media redaction, bounded waits, and failure bundles with redacted diagnostics.

---

## Quickstart

### 1. First render (2 minutes)

```bash
pip install terminal-demo-studio
tds init --destination my_demo
tds render my_demo/screenplays/getting_started.yaml --mode scripted --local --output gif --output-dir my_demo/outputs
```

Your GIF is in `my_demo/outputs/`. Use `--docker` instead of `--local` if you don't have vhs/ffmpeg installed &mdash; Docker bundles everything automatically.

### 2. Connect your agent (30 seconds)

Give Claude Code, Cursor, or Windsurf full access to render, validate, lint, and debug demos &mdash; no shell parsing needed.

<details>
<summary><b>Claude Code</b></summary>

```bash
pip install terminal-demo-studio[mcp]
claude mcp add terminal-demo-studio -- tds-mcp
```

Done. Claude Code can now call `tds_render`, `tds_validate`, `tds_lint`, `tds_debug`, `tds_list_templates`, and `tds_doctor` as native tools.

</details>

<details>
<summary><b>Cursor / Windsurf / any MCP client</b></summary>

```bash
pip install terminal-demo-studio[mcp]
```

Add to your project's `.mcp.json`:

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

The agent now has 6 tools available: `tds_render`, `tds_validate`, `tds_lint`, `tds_debug`, `tds_list_templates`, `tds_doctor`.

</details>

<details>
<summary><b>Any agent via CLI output contract</b></summary>

No MCP needed. Every `tds render` emits machine-readable keys that any agent can parse:

```bash
tds render screenplay.yaml --mode scripted --output gif --output-dir outputs
```

```
STATUS=success
RUN_DIR=outputs/.terminal_demo_studio_runs/run-abc123
MEDIA_GIF=outputs/.terminal_demo_studio_runs/run-abc123/media/demo.gif
SUMMARY=outputs/.terminal_demo_studio_runs/run-abc123/summary.json
```

Add this to your agent's system prompt or CLAUDE.md:

```text
Use `tds render <screenplay> --mode scripted --output gif --output-dir outputs` to render terminal demos.
Parse STATUS, RUN_DIR, and MEDIA_GIF from stdout.
If STATUS=failed, run `tds debug <RUN_DIR> --json` and fix the screenplay.
```

</details>

### 3. Keep demos fresh in CI (1 minute)

Add this workflow to auto-render GIFs whenever screenplays or source code change on `main`:

```yaml
# .github/workflows/auto-update-media.yml
name: auto-update-demo-media
on:
  push:
    branches: [main]
    paths:
      - 'examples/showcase/**/*.yaml'
      - 'your_package/**'             # your source code path

jobs:
  render:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 2 }

      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: pip }

      - uses: actions/setup-go@v5
        with: { go-version: "1.22" }

      - name: Install dependencies
        run: |
          sudo apt-get update && sudo apt-get install -y ffmpeg ttyd
          go install github.com/charmbracelet/vhs@v0.10.0
          echo "$HOME/go/bin" >> "$GITHUB_PATH"
          pip install -e .

      - name: Render and commit
        run: |
          mkdir -p docs/media
          for f in examples/showcase/*.yaml; do
            stem=$(basename "$f" .yaml)
            tds render "$f" --mode scripted_vhs --local --output gif --output-dir outputs || true
            find outputs -name "${stem}.*" -path "*/media/*" -exec cp {} docs/media/ \; 2>/dev/null || true
          done
          git config user.email "action@github.com"
          git config user.name "github-actions"
          git add docs/media/
          git diff --cached --quiet || (git commit -m "ci: auto-update demo media" && git push)
```

Or use the built-in composite action for per-PR rendering:

```yaml
- uses: tomallicino/terminal-demo-studio/.github/actions/render@main
  with:
    screenplay: examples/showcase/onboarding_tokyo_neon.yaml
    mode: scripted_vhs
    outputs: gif
    upload_artifact: true
```

See the [GitHub Action guide](docs/github-action.md) for full options.

### 4. Live editing loop

Watch a screenplay and auto-render on every save:

```bash
tds watch screenplay.yaml --mode scripted --output gif --output-dir outputs
```

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

## Showcase gallery

Every GIF below was generated from a YAML screenplay in this repo. Each one is fully reproducible &mdash; clone, render, done.

### Real agent TUI capture

The visual lane captures real interactive TUIs with live keyboard interaction, approval-prompt handling, and full-screen recording.

<table>
<tr>
<td width="50%">

**Claude Code** &mdash; real onboarding flow with OAuth prompts and interactive session

![Claude Code](docs/media/autonomous_claude_real_short.gif)

[GIF](docs/media/autonomous_claude_real_short.gif) &middot; [MP4](docs/media/autonomous_claude_real_short.mp4) &middot; [YAML](examples/showcase/autonomous_claude_real_short.yaml)

</td>
<td width="50%">

**Codex** &mdash; builds and verifies a hello-world app through the Codex TUI

![Codex](docs/media/autonomous_codex_real_short.gif)

[GIF](docs/media/autonomous_codex_real_short.gif) &middot; [MP4](docs/media/autonomous_codex_real_short.mp4) &middot; [YAML](examples/showcase/autonomous_codex_real_short.yaml)

</td>
</tr>
</table>

### Themed scripted demos

Pixel-perfect renders across six popular terminal themes. Each uses a different font, color scheme, and workflow pattern.

| Demo | Theme | Font | Preview |
|------|-------|------|---------|
| [Onboarding Neon](examples/showcase/onboarding_tokyo_neon.yaml) | TokyoNightStorm | Menlo | ![](docs/media/onboarding_tokyo_neon.gif) |
| [Bugfix Glow](examples/showcase/bugfix_catppuccin_glow.yaml) | Catppuccin Mocha | Monaco | ![](docs/media/bugfix_catppuccin_glow.gif) |
| [Recovery Retro](examples/showcase/recovery_gruvbox_retro.yaml) | GruvboxDark | Courier New | ![](docs/media/recovery_gruvbox_retro.gif) |
| [Policy Guard](examples/showcase/policy_nord_guard.yaml) | Nord | SF Mono | ![](docs/media/policy_nord_guard.gif) |
| [Menu Contrast](examples/showcase/menu_dracula_contrast.yaml) | Dracula | Courier | ![](docs/media/menu_dracula_contrast.gif) |
| [Nightshift Speedrun](examples/showcase/speedrun_nightshift.yaml) | TokyoNightStorm | Monaco | ![](docs/media/speedrun_nightshift.gif) |

### Starter patterns

Ready-to-use templates that demonstrate common demo patterns. Great starting points for your own screenplays.

| Demo | Pattern | Preview |
|------|---------|---------|
| [Install First Command](examples/mock/install_first_command.yaml) | Quickstart onboarding &mdash; pip install, first render, output | ![](docs/media/install_first_command.gif) |
| [Before & After Bugfix](examples/mock/before_after_bugfix.yaml) | Two-scene comparison &mdash; failing tests, then the fix | ![](docs/media/before_after_bugfix.gif) |
| [Error Then Fix](examples/mock/error_then_fix.yaml) | Error diagnosis &mdash; stack trace, root cause, resolution | ![](docs/media/error_then_fix.gif) |
| [Interactive Menu](examples/mock/interactive_menu_showcase.yaml) | TUI navigation &mdash; arrow keys, selection, confirmation | ![](docs/media/interactive_menu_showcase.gif) |
| [Policy Warning Gate](examples/mock/policy_warning_gate.yaml) | Safety enforcement &mdash; blocked action, policy explanation | ![](docs/media/policy_warning_gate.gif) |
| [Speedrun Cuts](examples/mock/speedrun_cuts.yaml) | CI pipeline &mdash; lint, test, build, deploy in rapid sequence | ![](docs/media/speedrun_cuts.gif) |

Regenerate all showcase media:

```bash
./scripts/render_showcase_media.sh
```

---

## Screenplay catalog

**28 screenplays** ship with the repo across three categories. Use them as-is or as templates for your own demos.

### Showcase (`examples/showcase/`) &mdash; polished, theme-styled demos

| Screenplay | Lane | Theme |
|------------|------|-------|
| [`onboarding_tokyo_neon.yaml`](examples/showcase/onboarding_tokyo_neon.yaml) | scripted | TokyoNightStorm |
| [`bugfix_catppuccin_glow.yaml`](examples/showcase/bugfix_catppuccin_glow.yaml) | scripted | Catppuccin Mocha |
| [`recovery_gruvbox_retro.yaml`](examples/showcase/recovery_gruvbox_retro.yaml) | scripted | GruvboxDark |
| [`policy_nord_guard.yaml`](examples/showcase/policy_nord_guard.yaml) | scripted | Nord |
| [`menu_dracula_contrast.yaml`](examples/showcase/menu_dracula_contrast.yaml) | scripted | Dracula |
| [`speedrun_nightshift.yaml`](examples/showcase/speedrun_nightshift.yaml) | scripted | TokyoNightStorm |
| [`autonomous_claude_real_short.yaml`](examples/showcase/autonomous_claude_real_short.yaml) | autonomous_video | TokyoNightStorm |
| [`autonomous_codex_real_short.yaml`](examples/showcase/autonomous_codex_real_short.yaml) | autonomous_video | GruvboxDark |

### Mock (`examples/mock/`) &mdash; lightweight patterns for testing and learning

| Screenplay | Pattern |
|------------|---------|
| [`install_first_command.yaml`](examples/mock/install_first_command.yaml) | Quickstart onboarding |
| [`before_after_bugfix.yaml`](examples/mock/before_after_bugfix.yaml) | Two-scene before/after |
| [`error_then_fix.yaml`](examples/mock/error_then_fix.yaml) | Error diagnosis and fix |
| [`interactive_menu_showcase.yaml`](examples/mock/interactive_menu_showcase.yaml) | Arrow-key TUI menu |
| [`policy_warning_gate.yaml`](examples/mock/policy_warning_gate.yaml) | Safety policy gate |
| [`speedrun_cuts.yaml`](examples/mock/speedrun_cuts.yaml) | Rapid CI pipeline |
| [`agent_loop.yaml`](examples/mock/agent_loop.yaml) | Agent tool-call loop |
| [`list_detail_flow.yaml`](examples/mock/list_detail_flow.yaml) | List &rarr; detail drill-down |
| [`safety_wizard.yaml`](examples/mock/safety_wizard.yaml) | Multi-step safety wizard |
| [`render_smoke.yaml`](examples/mock/render_smoke.yaml) | Minimal smoke test |
| [`autonomous_video_claude_like.yaml`](examples/mock/autonomous_video_claude_like.yaml) | Mock Claude TUI |
| [`autonomous_video_codex_like.yaml`](examples/mock/autonomous_video_codex_like.yaml) | Mock Codex TUI |

### Real (`examples/real/`) &mdash; actual agent executions for integration testing

| Screenplay | Description |
|------------|-------------|
| [`autonomous_video_codex_cli.yaml`](examples/real/autonomous_video_codex_cli.yaml) | Codex CLI basic session |
| [`autonomous_video_codex_complex_verified.yaml`](examples/real/autonomous_video_codex_complex_verified.yaml) | Complex multi-step Codex workflow |
| [`autonomous_video_codex_hello_project_approval.yaml`](examples/real/autonomous_video_codex_hello_project_approval.yaml) | Codex with approval prompts accepted |
| [`autonomous_video_codex_hello_project_deny.yaml`](examples/real/autonomous_video_codex_hello_project_deny.yaml) | Codex with approval prompts denied |
| [`autonomous_video_codex_multiturn.yaml`](examples/real/autonomous_video_codex_multiturn.yaml) | Multi-turn Codex conversation |
| [`autonomous_video_codex_patch_flow.yaml`](examples/real/autonomous_video_codex_patch_flow.yaml) | Codex patch review flow |
| [`real_agent_demo.yaml`](examples/real/real_agent_demo.yaml) | General agent demo session |

### Production screenplays (`screenplays/`) &mdash; complete workflow demos

| Screenplay | Theme | What it demonstrates |
|------------|-------|---------------------|
| [`dev_bugfix_workflow.yaml`](screenplays/dev_bugfix_workflow.yaml) | TokyoNightStorm | Developer bugfix: regression in `add()`, unit tests fail, fix, tests pass |
| [`drift_protection.yaml`](screenplays/drift_protection.yaml) | TokyoNightStorm | Drift protection: unsafe tool execution vs. policy-guarded safe mode |
| [`single_prompt_macos_demo.yaml`](screenplays/single_prompt_macos_demo.yaml) | TokyoNightStorm | Log triage with macOS-style prompt, failure parsing, error pattern display |
| [`rust_cli_demo.yaml`](screenplays/rust_cli_demo.yaml) | Catppuccin Mocha | Rust binary safety guard: unguarded deletion vs. policy-checked execution |
| [`agent_generated_feature_flag_fix.yaml`](screenplays/agent_generated_feature_flag_fix.yaml) | Nord | Feature flag bugfix: checkout flag misconfigured, tests fail, reconfigure, pass |
| [`agent_generated_policy_guard.yaml`](screenplays/agent_generated_policy_guard.yaml) | Catppuccin Mocha | Agent safety policy: raw PII export blocked, routed to secure vault |
| [`agent_generated_release_check.yaml`](screenplays/agent_generated_release_check.yaml) | GruvboxDark | Release compliance: lockfile, security scan, changelog, approver signoff |
| [`agent_generated_triage.yaml`](screenplays/agent_generated_triage.yaml) | Catppuccin Mocha | Agent triage: unguided output fails validation vs. guided output passes |

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

See the [Quickstart](#3-keep-demos-fresh-in-ci-1-minute) for setup. Full options in the [GitHub Action guide](docs/github-action.md).

| Input | Default | Description |
|-------|---------|-------------|
| `screenplay` | (required) | Screenplay YAML path |
| `mode` | `scripted_vhs` | Execution lane |
| `outputs` | `gif` | Comma-separated formats (`gif`, `mp4`) |
| `output_dir` | `outputs` | Output directory |
| `upload_artifact` | `true` | Upload run directory as artifact |
| `comment_pr` | `false` | Post result comment on PRs |

---

## Agent integration

See the [Quickstart](#2-connect-your-agent-30-seconds) for setup. Once connected, agents have access to 6 MCP tools:

| Tool | What it does |
|------|-------------|
| `tds_render` | Render a screenplay to GIF/MP4 |
| `tds_validate` | Parse and validate screenplay YAML |
| `tds_lint` | Check for policy and safety violations |
| `tds_debug` | Inspect run artifacts and failure diagnostics |
| `tds_list_templates` | List available screenplay templates |
| `tds_doctor` | Check environment readiness |

### Example agent prompt

```text
Render examples/showcase/policy_nord_guard.yaml in scripted mode.
Return STATUS, RUN_DIR, MEDIA_GIF, MEDIA_MP4, and SUMMARY.
If status is failed, run `tds debug <run_dir> --json` and summarize root cause.
```

### Autonomous workflow

An agent with TDS connected can maintain your demo media end-to-end:

1. **Create** &mdash; `tds_list_templates` &rarr; pick a template &rarr; write a screenplay
2. **Validate** &mdash; `tds_validate` to catch schema errors before rendering
3. **Lint** &mdash; `tds_lint --strict` to enforce safety policies
4. **Render** &mdash; `tds_render` to produce the GIF/MP4
5. **Debug** &mdash; if render fails, `tds_debug` reads the failure bundle and suggests fixes
6. **Watch** &mdash; `tds watch` for live iteration during screenplay editing

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
