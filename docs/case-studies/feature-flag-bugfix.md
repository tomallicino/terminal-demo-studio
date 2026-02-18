# Case Study: Feature Flag Bugfix Demo

## Goal

Show a clear before/after workflow where a failing feature-flag test is diagnosed and fixed in a deterministic terminal demo.

## Source Screenplay

- `screenplays/agent_generated_feature_flag_fix.yaml`

## Workflow

1. Validate screenplay structure and wait targets.
2. Render in local scripted mode with deterministic preinstall setup.
3. Inspect generated media and debug summary for narrative clarity.

## Command Set

```bash
tds validate screenplays/agent_generated_feature_flag_fix.yaml --explain
tds render screenplays/agent_generated_feature_flag_fix.yaml --mode scripted_vhs --local --output-dir outputs
```

## Key Scene Design

- **Before Fix**: `checkout_v2` is disabled and test assertion fails.
- **After Fix**: flag is enabled and the same test passes with `OK`.
- Wait checkpoints are pinned to stable lines (`FAIL:` and `OK`) for resilient playback timing.

## Result

Deterministic side-by-side demo suitable for README and launch artifacts.
