#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  source plugin/lib/state.sh
  source plugin/lib/loop.sh
  state_init main
  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    {
      "id": "m1",
      "title": "Scaffold",
      "status": "in-progress",
      "tasks": [
        {"id": "T01", "title": "Run giget", "status": "done", "kind": "scaffold"},
        {"id": "T02", "title": "Apply tailwind recipe", "status": "pending", "kind": "scaffold"},
        {"id": "T03", "title": "Add login form", "status": "pending", "kind": "feature", "depends_on": ["T02"]}
      ]
    },
    {
      "id": "m2",
      "title": "Polish",
      "status": "pending",
      "tasks": [
        {"id": "T04", "title": "Write README", "status": "pending", "kind": "doc"}
      ]
    }
  ]
}
EOF
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "pick_next_task picks the first non-blocked pending task in the active milestone" {
  run pick_next_task
  [ "$status" -eq 0 ]
  [ "$output" = "T02" ]
}

@test "pick_next_task respects depends_on" {
  # T03 depends on T02 which is still pending; pick_next_task must NOT return T03
  run pick_next_task
  [ "$output" != "T03" ]
}

@test "pick_next_task returns empty when active milestone has no actionable tasks" {
  jq '(.milestones[0].tasks[1].status) = "done"' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"
  jq '(.milestones[0].tasks[2].status) = "done"' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"
  run pick_next_task
  [ "$output" = "" ]
}

@test "mark_task_done flips a task status and writes decisions entry" {
  mark_task_done T02 "Applied tailwind via shadcn-style recipe"
  run jq -r '.milestones[0].tasks[1].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]
  grep -q "T02" "$FRINKLOOP_DIR/decisions.md"
}

@test "queue_fix_task adds a fix task with kind=fix and depends_on parent" {
  queue_fix_task T03 "form submit handler crashes on empty input"
  run jq -r '.milestones[0].tasks | length' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" -eq 4 ]
  run jq -r '.milestones[0].tasks[3].kind' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "fix" ]
  run jq -r '.milestones[0].tasks[3].depends_on[0]' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "T03" ]
}

@test "mark_milestone_done flips milestone status when all tasks done" {
  mark_task_done T02 "ok"
  mark_task_done T03 "ok"
  mark_milestone_done m1
  run jq -r '.milestones[0].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]
}

@test "active_milestone returns the first in-progress or pending milestone" {
  run active_milestone
  [ "$output" = "m1" ]
}
