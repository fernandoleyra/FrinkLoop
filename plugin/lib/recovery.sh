#!/usr/bin/env bash
# FrinkLoop crash recovery: detect mid-loop user edits, open blockers.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# Returns 0 if working tree is clean, 1 if dirty.
detect_dirty_tree() {
  local out
  out=$(git status --porcelain 2>/dev/null)
  if [ -z "$out" ]; then
    return 0
  fi
  return 1
}

open_blocker() {
  local task_id="$1"
  local reason="$2"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf "\n## %s — BLOCKED on %s\n%s\n" "$ts" "$task_id" "$reason" >> "$FRINKLOOP_DIR/blockers.md"
}

# Decides whether to resume the loop or open a blocker.
# Prints "resume" or "block" to stdout.
resume_or_block() {
  if detect_dirty_tree; then
    echo "resume"
    return 0
  fi
  open_blocker "<resume>" "Working tree dirty on resume — user may have edited files mid-loop. Manual cleanup required before resume."
  echo "block"
}
