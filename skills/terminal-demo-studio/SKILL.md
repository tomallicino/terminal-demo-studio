---
name: terminal-demo-studio
description: Build deterministic terminal/TUI demos with portable mock defaults and autonomous closed-loop execution for advanced workflows.
---

# terminal-demo-studio

Create reproducible terminal demo assets that are plug-and-play for agents and users.

## Install (Remote-First)

```bash
npx skills add tomallicino/terminal-demo-studio --skill terminal-demo-studio
```

## Start Here (Portable-First)

Portable mock demos are the default because they are deterministic and cross-platform.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

studio init
studio validate screenplays/getting_started.yaml --explain
studio run screenplays/getting_started.yaml --mode scripted_vhs --local --output-dir outputs --output gif
```

## Modes

1. `scripted_vhs`
- deterministic cinematic rendering from screenplay actions.

2. `autonomous_pty`
- closed-loop execution with waits/assertions.
- writes run artifacts (`events.jsonl`, `summary.json`, and failure bundle on error).
- command/assert flows are reliable in v1.
- interactive key/hotkey/input autonomy is specified in `docs/autonomous-roadmap.md` and not release-complete yet.

## Advanced Real-Tool Lane

Use `examples/real/` for optional advanced external-tool sessions.

Rules:

1. Keep public onboarding and README demos on portable mocks.
2. Use `--mode autonomous_pty` with explicit waits/assertions.
3. Treat retries/timeouts as explicit screenplay policy, not hidden runtime behavior.

## Anti-Flake Checklist

1. Prefer explicit `assert_screen_regex` and `wait_screen_regex` markers.
2. Keep steps short and stateful; avoid giant command chains.
3. Use portable mocks for default docs and screenshots.
4. Keep advanced real-tool demos isolated and clearly labeled.
