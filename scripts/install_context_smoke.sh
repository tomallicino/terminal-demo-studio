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
studio new --list-templates > templates.txt
if ! grep -Eq '^- dev_bugfix$' templates.txt; then
  echo "Installed-context smoke failed: dev_bugfix template not listed"
  cat templates.txt
  exit 1
fi

studio new smoke_case --template dev_bugfix --destination screenplays >/dev/null
studio validate screenplays/smoke_case.yaml --explain >/dev/null

echo "Installed-context smoke checks passed"
