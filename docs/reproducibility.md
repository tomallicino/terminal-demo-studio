# Reproducibility Guarantees

`terminal-demo-studio` is built for deterministic demo outputs when inputs and environment are controlled.

## Deterministic Inputs

- Screenplay YAML content
- Terminal geometry (`settings.width`, `settings.height`, `padding`, `margin`)
- Playback settings (`playback`, framerate, waits/sleeps)
- Theme and prompt settings
- Execution lane (`scripted_vhs` vs `autonomous_pty` vs `autonomous_video`)

## Toolchain Knobs

- Python package version (`terminal-demo-studio`)
- VHS version (`v0.10.0` recommended)
- FFmpeg/FFprobe availability and drawtext support
- Pillow fallback for label rendering when drawtext is missing

## Environment Recommendations

- Pin locale (`LANG`, `LC_ALL`) to avoid output variations.
- Keep shell behavior stable (`bash`/`zsh`/`pwsh` choice).
- Use fixed dependencies in CI and local environments.
- For team-wide parity, prefer containerized rendering with pinned image tags.
- Default Docker image retention keeps recent hashed tags and prunes stale ones to reduce local disk drift (`TDS_DOCKER_IMAGE_RETENTION`).

## What Is Stable

- Scripted lane media composition and run artifact structure
- Template expansion and schema validation
- Run summary and debug bundle shape

## What May Vary

- Real external tool output in advanced demos
- Autonomous command lane timing under loaded systems
- Fonts available on host machines (when custom fonts are used)

## Canonical Run Artifacts

Each run writes a canonical directory:

- `run_dir/manifest.json`
- `run_dir/summary.json`
- `run_dir/media/*.gif|*.mp4`
- `run_dir/scenes/scene_*.mp4` (scripted lane)
- `run_dir/tapes/scene_*.tape` (scripted lane)
- `run_dir/runtime/events.jsonl` (autonomous lane)
- `run_dir/failure/*` when failed

These files are the source of truth for debugging and CI verification.
