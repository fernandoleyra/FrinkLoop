#!/usr/bin/env bash
# FrinkLoop Stop hook.
# Exit 0 → let the session end.
# Exit 2 → continue the loop (Claude Code re-prompts the model).
# FRINKLOOP_DIR must be exported by the session preamble.

set -euo pipefail

: "${FRINKLOOP_DIR:=}"

if [ -z "$FRINKLOOP_DIR" ] || [ ! -f "$FRINKLOOP_DIR/state.json" ]; then
  exit 0
fi

status=$(jq -r '.status' "$FRINKLOOP_DIR/state.json")

case "$status" in
  done|paused|blocked|quota-stopped|idle)
    exit 0
    ;;
  running)
    if [ ! -f "$FRINKLOOP_DIR/tasks.json" ]; then
      exit 0
    fi
    pending_count=$(jq '[.milestones[].tasks[] | select(.status == "pending")] | length' "$FRINKLOOP_DIR/tasks.json")
    if [ "$pending_count" -gt 0 ]; then
      exit 2
    fi
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
