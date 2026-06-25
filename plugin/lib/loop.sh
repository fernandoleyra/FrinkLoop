#!/usr/bin/env bash
# FrinkLoop loop helpers — task picking, status mutations, decisions log.
# Caller must export FRINKLOOP_DIR and source plugin/lib/state.sh first.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# Returns the id of the first in-progress or pending milestone, or empty string.
active_milestone() {
  jq -r '
    .milestones[]
    | select(.status == "in-progress" or .status == "pending")
    | .id
  ' "$FRINKLOOP_DIR/tasks.json" | head -1
}

# Returns the task id of the next task to work on, or empty string if none.
# Skips tasks whose depends_on still contain pending task ids.
pick_next_task() {
  local mid
  mid=$(active_milestone)
  if [ -z "$mid" ]; then
    echo ""
    return 0
  fi

  jq -r --arg mid "$mid" '
    (.milestones[] | select(.id == $mid) | .tasks) as $tasks
    | ($tasks | map(select(.status == "pending")) | map(.id)) as $pending_ids
    | $tasks
    | map(select(.status == "pending"))
    | map(select(
        ((.depends_on // []) | length == 0)
        or
        ((.depends_on // []) | all(. as $dep | $pending_ids | index($dep) | . == null))
      ))
    | .[0].id // ""
  ' "$FRINKLOOP_DIR/tasks.json"
}

# Mark a task done by id; append an entry to decisions.md.
mark_task_done() {
  local task_id="$1"
  local note="${2:-}"
  local path="$FRINKLOOP_DIR/tasks.json"
  local tmp
  tmp=$(mktemp)
  jq --arg tid "$task_id" '
    .milestones |= map(
      .tasks |= map(
        if .id == $tid then .status = "done" else . end
      )
    )
  ' "$path" > "$tmp"
  mv "$tmp" "$path"

  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf "\n## %s — %s\n%s\n" "$ts" "$task_id" "$note" >> "$FRINKLOOP_DIR/decisions.md"
}

# Queue a new fix task that depends on parent_task_id.
# Appends the fix task to the active milestone and returns the new task id.
queue_fix_task() {
  local parent="$1"
  local error_summary="$2"
  local path="$FRINKLOOP_DIR/tasks.json"
  local mid
  mid=$(active_milestone)

  # Generate next id: T<N+1> zero-padded to 2 digits
  local next_id
  next_id=$(jq -r '
    [.milestones[].tasks[].id | ltrimstr("T") | tonumber] | max as $m
    | ($m + 1) as $n
    | "T" + (if $n < 10 then "0" else "" end) + ($n | tostring)
  ' "$path")

  local tmp
  tmp=$(mktemp)
  jq --arg mid "$mid" --arg pid "$parent" --arg nid "$next_id" --arg err "$error_summary" '
    .milestones |= map(
      if .id == $mid
      then .tasks += [{
        "id": $nid,
        "title": ("Fix: " + $err),
        "status": "pending",
        "kind": "fix",
        "depends_on": [$pid],
        "retries": 0
      }]
      else . end
    )
  ' "$path" > "$tmp"
  mv "$tmp" "$path"

  echo "$next_id"
}

# Mark a milestone done if and only if all its tasks are done.
# Returns 1 (no-op) if any task is still not done.
mark_milestone_done() {
  local mid="$1"
  local path="$FRINKLOOP_DIR/tasks.json"
  local all_done
  all_done=$(jq -r --arg mid "$mid" '
    .milestones[] | select(.id == $mid)
    | (.tasks | map(.status == "done") | all)
  ' "$path")
  if [ "$all_done" != "true" ]; then
    return 1
  fi
  local tmp
  tmp=$(mktemp)
  jq --arg mid "$mid" '
    .milestones |= map(if .id == $mid then .status = "done" else . end)
  ' "$path" > "$tmp"
  mv "$tmp" "$path"
}
