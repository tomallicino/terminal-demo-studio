#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

if ! command -v tds >/dev/null 2>&1; then
  python3 -m pip install -e '.[dev]'
fi

mkdir -p docs/media outputs

scripted_screenplays=(
  "examples/showcase/onboarding_tokyo_neon.yaml"
  "examples/showcase/bugfix_catppuccin_glow.yaml"
  "examples/showcase/recovery_gruvbox_retro.yaml"
  "examples/showcase/policy_nord_guard.yaml"
  "examples/showcase/menu_dracula_contrast.yaml"
  "examples/showcase/speedrun_nightshift.yaml"
)

visual_screenplays=(
  "examples/showcase/autonomous_codex_real_short.yaml"
  "examples/showcase/autonomous_claude_real_short.yaml"
)

extract_field() {
  local field="$1"
  awk -F= -v key="$field" '$1 == key {print substr($0, index($0, "=") + 1)}' | tail -1
}

render_and_copy() {
  local screenplay="$1"
  local mode="$2"
  local runtime_flag="$3"
  local asset_name
  local render_output
  local media_gif
  local media_mp4

  asset_name="$(basename "$screenplay" .yaml)"
  echo "Rendering $screenplay ($mode, $runtime_flag)"

  render_output="$(
    tds render "$screenplay" \
      --mode "$mode" \
      "$runtime_flag" \
      --output gif \
      --output mp4 \
      --output-dir outputs
  )"
  printf '%s\n' "$render_output"

  media_gif="$(printf '%s\n' "$render_output" | extract_field "MEDIA_GIF")"
  media_mp4="$(printf '%s\n' "$render_output" | extract_field "MEDIA_MP4")"

  if [[ -z "$media_gif" || -z "$media_mp4" ]]; then
    echo "Failed to find media outputs for $screenplay"
    return 1
  fi

  cp "$media_gif" "docs/media/${asset_name}.gif"
  cp "$media_mp4" "docs/media/${asset_name}.mp4"
  echo "Wrote docs/media/${asset_name}.gif and docs/media/${asset_name}.mp4"
}

for screenplay in "${scripted_screenplays[@]}"; do
  tds validate "$screenplay" --explain >/dev/null
  render_and_copy "$screenplay" "scripted_vhs" "--local"
done

for screenplay in "${visual_screenplays[@]}"; do
  tds validate "$screenplay" --explain >/dev/null
  render_and_copy "$screenplay" "autonomous_video" "--docker"
done

echo "Showcase media render complete"
