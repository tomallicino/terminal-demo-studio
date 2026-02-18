#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}"
SCREENPLAY="${1:-${REPO_ROOT}/screenplays/dev_bugfix_workflow.yaml}"
if [[ $# -gt 0 ]]; then
  shift
fi

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
python3 -m terminal_demo_studio.cli run "${SCREENPLAY}" --mode auto "$@"
