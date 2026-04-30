#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  source "$PLUGIN_LIB_DIR/state.sh"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "stop hook exits 0 when state.json is missing" {
  STOP_HOOK="$(cd "$BATS_TEST_DIRNAME/../../plugin/hooks" && pwd)/stop.sh"
  run "$STOP_HOOK"
  [ "$status" -eq 0 ]
}

@test "stop hook exits 0 when status is done" {
  state_init main
  state_set status done
  STOP_HOOK="$(cd "$BATS_TEST_DIRNAME/../../plugin/hooks" && pwd)/stop.sh"
  run "$STOP_HOOK"
  [ "$status" -eq 0 ]
}

@test "stop hook exits 0 when status is paused" {
  state_init main
  state_set status paused
  STOP_HOOK="$(cd "$BATS_TEST_DIRNAME/../../plugin/hooks" && pwd)/stop.sh"
  run "$STOP_HOOK"
  [ "$status" -eq 0 ]
}

@test "stop hook exits 2 when status is running and tasks pending" {
  state_init main
  state_set status running
  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "x", "status": "in-progress",
      "tasks": [{"id": "T01", "title": "x", "status": "pending", "kind": "feature"}]
    }
  ]
}
EOF
  STOP_HOOK="$(cd "$BATS_TEST_DIRNAME/../../plugin/hooks" && pwd)/stop.sh"
  run "$STOP_HOOK"
  [ "$status" -eq 2 ]
}

@test "stop hook exits 0 when status is running but no pending tasks" {
  state_init main
  state_set status running
  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "x", "status": "done",
      "tasks": [{"id": "T01", "title": "x", "status": "done", "kind": "feature"}]
    }
  ]
}
EOF
  STOP_HOOK="$(cd "$BATS_TEST_DIRNAME/../../plugin/hooks" && pwd)/stop.sh"
  run "$STOP_HOOK"
  [ "$status" -eq 0 ]
}

@test "post-iteration hook increments iteration_count and appends a log line" {
  state_init main
  POST_ITER_HOOK="$(cd "$BATS_TEST_DIRNAME/../../plugin/hooks" && pwd)/post-iteration.sh"
  run "$POST_ITER_HOOK"
  [ "$status" -eq 0 ]
  run jq -r '.iteration_count' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "1" ]
  [ -f "$FRINKLOOP_DIR/iteration-log.jsonl" ]
  run wc -l < "$FRINKLOOP_DIR/iteration-log.jsonl"
  [ "$output" -eq 1 ]
}
