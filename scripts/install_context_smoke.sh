#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

python3 -m venv "$TMP_ROOT/venv"
# shellcheck disable=SC1091
source "$TMP_ROOT/venv/bin/activate"
python -m pip install --upgrade pip >/dev/null
pip install "$ROOT_DIR" >/dev/null

cd "$TMP_ROOT"
tds new --list-templates > templates.txt
if ! grep -Eq '^- install_first_command$' templates.txt; then
  echo "Installed-context smoke failed: install_first_command template not listed"
  cat templates.txt
  exit 1
fi

tds new smoke_case --template install_first_command --destination screenplays >/dev/null
tds validate screenplays/smoke_case.yaml --explain >/dev/null
tds render screenplays/smoke_case.yaml --mode scripted_vhs --local --output gif --output-dir outputs >/dev/null

echo "Installed-context smoke checks passed"
