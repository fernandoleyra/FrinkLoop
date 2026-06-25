#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  source plugin/lib/state.sh
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "state_init creates a valid state.json" {
  state_init main
  [ -f "$FRINKLOOP_DIR/state.json" ]
  run jq -r '.status' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "idle" ]
  run jq -r '.iteration_count' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "0" ]
  run jq -r '.branch' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "main" ]
}

@test "state_get returns a field value" {
  state_init main
  run state_get status
  [ "$status" -eq 0 ]
  [ "$output" = "idle" ]
}

@test "state_set updates a field and round-trips" {
  state_init main
  state_set status running
  run state_get status
  [ "$output" = "running" ]
}

@test "log_iteration appends a JSONL line" {
  state_init main
  log_iteration '{"event":"task_done","task_id":"T01"}'
  log_iteration '{"event":"task_done","task_id":"T02"}'
  run wc -l < "$FRINKLOOP_DIR/iteration-log.jsonl"
  [ "$output" -eq 2 ]
}

@test "state_validate against schema passes for fresh state" {
  state_init main
  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d "$FRINKLOOP_DIR/state.json" --strict=false
  [ "$status" -eq 0 ]
}

@test "state_increment_iteration stamps last_iteration_at" {
  state_init main
  state_increment_iteration
  run jq -r '.last_iteration_at' "$FRINKLOOP_DIR/state.json"
  [ "$status" -eq 0 ]
  [ "$output" != "null" ]
}
