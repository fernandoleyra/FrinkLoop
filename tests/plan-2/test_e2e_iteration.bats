#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/proj"
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"

  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"

  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t

  source "$PLUGIN_DIR/lib/state.sh"
  source "$PLUGIN_DIR/lib/loop.sh"
  source "$PLUGIN_DIR/lib/verify.sh"
  source "$PLUGIN_DIR/lib/recovery.sh"

  state_init main
  state_set status running

  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "Setup", "status": "in-progress",
      "tasks": [
        {"id":"T01","title":"Write README","status":"pending","kind":"doc"}
      ]
    }
  ]
}
EOF

  echo "# initial" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "init"

  export PLUGIN_DIR REPO_DIR
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "one full iteration: pick → builder simulated → qa → mark done" {
  # 1. pick
  task_id=$(pick_next_task)
  [ "$task_id" = "T01" ]

  # 2. builder simulated: edit README and commit
  echo "## Hello" >> README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "doc(readme): expand"

  # 3. qa: run verify
  task_json=$(jq --arg tid "$task_id" '.milestones[].tasks[] | select(.id==$tid)' "$FRINKLOOP_DIR/tasks.json")
  run verify_task "$task_json"
  [ "$status" -eq 0 ]
  [ -f "$FRINKLOOP_DIR/qa.json" ]

  # 4. mark done
  mark_task_done "$task_id" "Expanded README"

  # 5. milestone complete → mark milestone done
  mark_milestone_done m1
  run jq -r '.milestones[0].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]

  # 6. final: state shows done after we set it explicitly
  state_set status done
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 0 ]   # status=done → stop hook lets session exit
}

@test "verify failure path: queue_fix_task gets called and Stop hook keeps looping" {
  task_id=$(pick_next_task)
  task_json=$(jq --arg tid "$task_id" '.milestones[].tasks[] | select(.id==$tid)' "$FRINKLOOP_DIR/tasks.json")

  # Force fail: change task kind to feature so verify expects tests/, which doesn't exist
  jq --arg tid "$task_id" '(.milestones[0].tasks[] | select(.id==$tid).kind) = "feature"' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"

  run verify_task "$(jq --arg tid "$task_id" '.milestones[].tasks[] | select(.id==$tid)' "$FRINKLOOP_DIR/tasks.json")"
  [ "$status" -ne 0 ]

  queue_fix_task "$task_id" "no tests dir"

  # New fix task added
  run jq -r '.milestones[0].tasks | length' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" -eq 2 ]

  # Stop hook should keep looping (status running, pending tasks exist)
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 2 ]
}
