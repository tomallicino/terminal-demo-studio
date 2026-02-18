---
name: terminal-demo-studio
description: Build deterministic terminal/TUI demos with portable mock defaults and autonomous closed-loop execution for advanced workflows.
---

# terminal-demo-studio

Create reproducible terminal demo assets that are plug-and-play for agents and users.

## Install

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

## Start Here (Portable-First)

Portable mock demos are the default because they are deterministic and cross-platform.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

studio doctor --mode auto
studio validate examples/mock/safety_wizard.yaml --explain
studio run examples/mock/safety_wizard.yaml --mode scripted_vhs --local --output-dir outputs --no-mp4
```

## Modes

1. `scripted_vhs`
- deterministic cinematic rendering from screenplay actions.

2. `autonomous_pty`
- closed-loop execution with waits/assertions.
- writes run artifacts (`events.jsonl`, `summary.json`, and failure bundle on error).
- command/assert flows are reliable in v1.
- interactive key/hotkey/input autonomy is not release-complete yet.

## Advanced Real-Tool Demos

Use `examples/real/` for real external-tool sessions.

Rules:

1. Keep README defaults on portable mocks.
2. Real vendor-named demos must include a manifest with tool version and capture date.
3. Use `--mode autonomous_pty` for advanced command/assert runs.

## Anti-Flake Checklist

1. Prefer explicit `assert_screen_regex` and `wait_screen_regex` markers.
2. Keep steps short and stateful; avoid giant command chains.
3. Use portable mocks for default documentation demos.
4. Keep advanced real-tool demos isolated and clearly labeled.
