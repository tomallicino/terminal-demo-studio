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

## Auto-update demo media on code changes

Add this workflow to automatically re-render showcase GIFs when screenplays or source code change on `main`:

```yaml
name: auto-update-demo-media

on:
  push:
    branches: [main]
    paths:
      - 'examples/showcase/**/*.yaml'
      - 'terminal_demo_studio/**'

jobs:
  render:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - uses: actions/setup-go@v5
        with:
          go-version: "1.22"

      - name: Install dependencies
        run: |
          sudo apt-get update && sudo apt-get install -y ffmpeg ttyd
          go install github.com/charmbracelet/vhs@v0.10.0
          echo "$HOME/go/bin" >> "$GITHUB_PATH"
          pip install -e .

      - name: Detect and render changed screenplays
        run: |
          changed=$(git diff HEAD~1 HEAD --name-only -- 'examples/showcase/*.yaml' || true)
          [ -z "$changed" ] && changed=$(ls examples/showcase/*.yaml 2>/dev/null || true)
          mkdir -p docs/media
          echo "$changed" | while IFS= read -r f; do
            [ -z "$f" ] || [ ! -f "$f" ] && continue
            stem=$(basename "$f" .yaml)
            tds render "$f" --mode scripted_vhs --local --output gif --output-dir outputs || true
            find outputs -name "${stem}.*" -path "*/media/*" -exec cp {} docs/media/ \; 2>/dev/null || true
          done

      - name: Commit updated media
        run: |
          git config user.email "action@github.com"
          git config user.name "github-actions"
          git add docs/media/
          git diff --cached --quiet || (git commit -m "ci: auto-update demo media" && git push)
```

This workflow:
- Triggers on pushes to `main` that touch screenplays or source code
- Detects which screenplays changed (or re-renders all if only source changed)
- Renders each screenplay in `scripted_vhs` mode
- Commits updated media back to the repository
