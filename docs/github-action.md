# GitHub Action: Render Terminal Demos

Use `.github/actions/render` to render a screenplay in CI, capture canonical outputs, and optionally post PR feedback.

## Quick start

```yaml
name: render-demo

on:
  pull_request:
  workflow_dispatch:

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Render demo
        id: render
        uses: ./.github/actions/render
        with:
          screenplay: examples/showcase/onboarding_tokyo_neon.yaml
          mode: scripted_vhs
          outputs: gif,mp4
          output_dir: outputs
          upload_artifact: true
          comment_pr: false

      - name: Print outputs
        run: |
          echo "status=${{ steps.render.outputs.status }}"
          echo "run_dir=${{ steps.render.outputs.run_dir }}"
          echo "media_paths=${{ steps.render.outputs.media_paths }}"
```

## Inputs

- `screenplay` (required): screenplay YAML path.
- `mode`: `scripted_vhs`, `autonomous_pty`, or `autonomous_video` (default: `scripted_vhs`).
- `outputs`: comma-separated output formats (`gif`, `mp4`) (default: `gif`).
- `output_dir`: output directory (default: `outputs`).
- `upload_artifact`: upload the run directory (default: `true`).
- `artifact_name`: artifact name template (default: `tds-render-${{ github.run_id }}`).
- `comment_pr`: post a result comment on PRs (default: `false`).
- `python_version`: action runtime Python version (default: `3.11`).

## Outputs

- `status`: render status (`success` or `failed`).
- `run_dir`: canonical run directory.
- `media_paths`: comma-separated media paths from `tds` output.

## Behavior notes

- The action installs `terminal-demo-studio` from the current repository checkout.
- Scripted dependencies are provisioned for Linux/macOS.
- Scripted mode in this composite action intentionally fails on Windows.
- Action runs `tds render ... --local`; use runner provisioning for visual mode dependencies.

## Recommended CI pattern

1. Run `tds validate` and `tds lint` before render for fast-fail behavior.
2. Keep one smoke render in every PR.
3. Upload the full `run_dir` artifact for reproducible debugging.
