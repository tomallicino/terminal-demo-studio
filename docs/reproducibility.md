# Reproducibility Guide

`terminal-demo-studio` is designed for deterministic output when screenplay input and runtime dependencies are controlled.

## Deterministic inputs

- Screenplay YAML (including `variables`, `preinstall`, `setup`, and `actions`).
- Visual settings (`width`, `height`, `theme`, `font_family`, spacing/padding).
- Playback mode (`sequential` vs `simultaneous`).
- Lane selection (`scripted_vhs`, `autonomous_pty`, `autonomous_video`).

## Runtime dependencies that matter

- `terminal-demo-studio` version.
- `vhs` version for scripted lane (recommended: `v0.10.0`).
- `ffmpeg` and `ffprobe` versions.
- drawtext support (if absent, label rendering uses Pillow overlay fallback).

## Environment controls

- Pin locale (`LANG`, `LC_ALL`) to avoid output drift in command text formatting.
- Keep shell choice stable per scenario (`bash`, `zsh`, `pwsh`, etc.).
- Prefer CI/containerized rendering for cross-machine consistency.
- For autonomous video, prefer explicit waits/assertions over timing assumptions.

## Docker controls

- `TDS_DOCKER_HARDENING=1` (default).
- `TDS_DOCKER_PIDS_LIMIT=512` (default).
- `TDS_DOCKER_NETWORK` (optional network policy).
- `TDS_DOCKER_READ_ONLY=1` (optional).
- `TDS_DOCKER_IMAGE_RETENTION=3` (default tag retention).

## What is stable by contract

- Canonical run directory structure.
- `summary.json` and `manifest.json` presence.
- CLI result keys (`STATUS`, `RUN_DIR`, `MEDIA_*`, `SUMMARY`, `EVENTS`).
- Screenplay schema validation behavior.

## What can vary

- Real tool output in non-mock demos.
- Host-specific fonts when using custom `font_family`.
- Autonomous timing on heavily loaded machines.

## Practical checklist

1. Run `tds doctor --mode scripted` (or `--mode visual` for autonomous video).
2. Validate screenplay with `tds validate <file> --explain`.
3. Lint autonomous policies with `tds lint <file> --strict`.
4. Render in a consistent mode and environment.
5. Archive `RUN_DIR` for reproducible debugging.
