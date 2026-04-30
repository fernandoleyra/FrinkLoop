#!/usr/bin/env bash
# FrinkLoop state I/O helpers.
# Reads/writes state.json and iteration-log.jsonl in $FRINKLOOP_DIR.
# Caller must export FRINKLOOP_DIR before sourcing.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set (e.g. <project>/.frinkloop)}"

state_init() {
  local branch="${1:-main}"
  local path="$FRINKLOOP_DIR/state.json"
  if [ -f "$path" ]; then
    return 0
  fi
  cat > "$path" <<EOF
{
  "schema_version": 1,
  "current_milestone": null,
  "current_task": null,
  "iteration_count": 0,
  "branch": "$branch",
  "last_verified_sha": null,
  "status": "idle"
}
EOF
}

state_get() {
  local field="$1"
  jq -r ".${field}" "$FRINKLOOP_DIR/state.json"
}

state_set() {
  local field="$1"
  local value="$2"
  local path="$FRINKLOOP_DIR/state.json"
  local tmp
  tmp=$(mktemp)
  if [[ "$value" =~ ^-?[0-9]+$ ]] || [[ "$value" == "true" ]] || [[ "$value" == "false" ]] || [[ "$value" == "null" ]]; then
    jq ".${field} = ${value}" "$path" > "$tmp"
  else
    jq --arg v "$value" ".${field} = \$v" "$path" > "$tmp"
  fi
  mv "$tmp" "$path"
}

state_increment_iteration() {
  local current
  current=$(state_get iteration_count)
  state_set iteration_count "$((current + 1))"
  state_set last_iteration_at "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
}

log_iteration() {
  local payload="$1"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "$payload" | jq -c --arg ts "$ts" '. + {ts: $ts}' >> "$FRINKLOOP_DIR/iteration-log.jsonl"
}
