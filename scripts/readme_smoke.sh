#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -e '.[dev]'

studio doctor --mode auto
tmp_workspace="$(mktemp -d)"
studio init --destination "$tmp_workspace"
studio validate "$tmp_workspace/screenplays/getting_started.yaml" --explain
studio validate examples/mock/safety_wizard.yaml --explain
studio run examples/mock/safety_wizard.yaml --mode scripted_vhs --local --output-dir outputs --output gif
studio run examples/mock/agent_loop.yaml --mode autonomous_pty --output-dir outputs

echo "README smoke checks passed"
