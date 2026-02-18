# GitHub Action: Render Terminal Demos

Use the reusable action at `.github/actions/render` to render a screenplay, upload artifacts, and optionally comment on pull requests.

## Quick Copy/Paste

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
          screenplay: examples/mock/install_first_command.yaml
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

- `screenplay` (required): path to screenplay YAML.
- `mode`: `scripted_vhs` or `autonomous_pty` (default `scripted_vhs`).
- `outputs`: comma-separated formats (`gif`, `mp4`) (default `gif`).
- `output_dir`: output directory (default `outputs`).
- `upload_artifact`: upload the run directory artifact (default `true`).
- `artifact_name`: artifact name (default `tds-render-${{ github.run_id }}`).
- `comment_pr`: comment summary on PR (default `false`).
- `python_version`: Python version (default `3.11`).

## Outputs

- `status`: run status (`success` or `failed`).
- `run_dir`: canonical run directory.
- `media_paths`: comma-separated media files discovered from `tds` output.

## Notes

- The action is portable for `autonomous_pty` mode.
- In this release, scripted rendering inside this action is installed for Linux/macOS.
- For scripted mode on Windows, use a local runner setup or defer to Linux/macOS workflows.
