#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

status=0

check_forbidden_paths() {
  local pattern="$1"
  local message="$2"
  local hits
  hits="$(git ls-files --cached --others --exclude-standard | grep -En "$pattern" || true)"
  if [[ -n "$hits" ]]; then
    echo "[FAIL] $message"
    echo "$hits"
    status=1
  fi
}

check_forbidden_content() {
  local pattern="$1"
  local message="$2"
  local hits
  hits="$(
    git ls-files --cached --others --exclude-standard \
      | grep -Ev '^docs/media/' \
      | grep -Ev '^scripts/release_preflight\.sh$' \
      | while read -r file; do
          [[ -f "$file" ]] || continue
          grep -IEn "$pattern" "$file" || true
        done
  )"
  if [[ -n "$hits" ]]; then
    echo "[FAIL] $message"
    echo "$hits"
    status=1
  fi
}

check_forbidden_paths '(^|/)AGENTS\.md$' 'AGENTS.md must not be part of public release content.'
check_forbidden_paths '(^|/)CLAUDE\.md$' 'CLAUDE.md must not be part of public release content.'
check_forbidden_paths '(^|/)task_plan\.md$|(^|/)findings\.md$|(^|/)progress\.md$' 'Internal planning files must not be tracked.'
check_forbidden_paths '(^|/)\.env(\.|$)' 'Environment files must not be tracked.'
check_forbidden_paths '\.DS_Store$|(^|/)__pycache__/|\.egg-info/' 'System/cache/build artifacts must not be tracked.'

check_forbidden_content '/Users/' 'Absolute local filesystem paths were detected in tracked text files.'
check_forbidden_content 'thomasallicino|MacBook-Pro' 'Personal identity markers were detected in tracked text files.'

if [[ $status -eq 0 ]]; then
  echo "[PASS] release preflight checks passed"
else
  exit 1
fi
