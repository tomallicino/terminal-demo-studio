#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -e '.[dev]'

tds doctor --mode auto
tmp_workspace="$(mktemp -d)"
tds init --destination "$tmp_workspace"
tds validate "$tmp_workspace/screenplays/getting_started.yaml" --explain
tds render --template install_first_command --name readme_quickstart --destination "$tmp_workspace/screenplays" --mode scripted_vhs --local --output gif --output-dir "$tmp_workspace/outputs"
tds validate examples/mock/agent_loop.yaml --explain
tds run examples/mock/agent_loop.yaml --mode autonomous_pty --output-dir "$tmp_workspace/outputs"

echo "README smoke checks passed"
