#!/usr/bin/env bash
# FrinkLoop post-iteration hook.
# Increments iteration_count and appends an iteration-log entry.
# FRINKLOOP_DIR must be exported.

set -euo pipefail

: "${FRINKLOOP_DIR:=}"

if [ -z "$FRINKLOOP_DIR" ] || [ ! -f "$FRINKLOOP_DIR/state.json" ]; then
  exit 0
fi

# Source state helpers via path relative to this hook.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOK_DIR/../lib/state.sh"

state_increment_iteration

iter=$(state_get iteration_count)
log_iteration "$(jq -nc --arg i "$iter" '{event:"iteration", iter:($i|tonumber)}')"

exit 0
