# Case Study: Feature-Flag Bugfix

This case study demonstrates a deterministic before/after debugging narrative that is suitable for release notes and README media.

## Goal

Show one failing path and one fixed path with explicit visual proof in terminal output.

## Screenplay

- `screenplays/agent_generated_feature_flag_fix.yaml`

## Runbook

```bash
tds validate screenplays/agent_generated_feature_flag_fix.yaml --explain
tds lint screenplays/agent_generated_feature_flag_fix.yaml
tds render screenplays/agent_generated_feature_flag_fix.yaml --mode scripted_vhs --local --output gif --output mp4 --output-dir outputs
```

## Why this works

- Uses deterministic preinstall setup for controlled input state.
- Uses explicit wait anchors for both failure and success states.
- Produces side-by-side narrative that is easy to review frame-by-frame.

## Success signals

- Scenario A contains failure markers (for example `FAIL` or explicit blocked state).
- Scenario B contains success markers (`OK`, pass, or equivalent release-ready state).
- `summary.json` reports `status: success` and includes media paths.
