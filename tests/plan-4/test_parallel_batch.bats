#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  source "$PLUGIN_LIB_DIR/state.sh"
  source "$PLUGIN_LIB_DIR/loop.sh"
  state_init main

  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "Build", "status": "in-progress",
      "tasks": [
        {"id":"T01","title":"Add login","status":"pending","kind":"feature","paths_touched":["src/auth/"]},
        {"id":"T02","title":"Add settings page","status":"pending","kind":"feature","paths_touched":["src/settings/"]},
        {"id":"T03","title":"Add billing page","status":"pending","kind":"feature","paths_touched":["src/billing/"]},
        {"id":"T04","title":"Refactor auth helper","status":"pending","kind":"feature","paths_touched":["src/auth/"]},
        {"id":"T05","title":"Update README","status":"pending","kind":"doc"}
      ]
    }
  ]
}
EOF
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "pick_parallel_batch returns up to N tasks with disjoint paths" {
  run pick_parallel_batch 10
  [ "$status" -eq 0 ]
  # Should return T01, T02, T03, T05 (T04 conflicts with T01 on src/auth/) — 4 ids
  echo "$output" | grep -q "T01"
  echo "$output" | grep -q "T02"
  echo "$output" | grep -q "T03"
  echo "$output" | grep -q "T05"
  ! echo "$output" | grep -q "T04"
}

@test "pick_parallel_batch respects the max parameter" {
  run pick_parallel_batch 2
  [ "$status" -eq 0 ]
  count=$(echo "$output" | wc -w)
  [ "$count" -eq 2 ]
}

@test "pick_parallel_batch returns empty when nothing is pending" {
  jq '.milestones[0].tasks |= map(.status = "done")' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"
  run pick_parallel_batch 10
  [ -z "$output" ]
}

@test "pick_parallel_batch always picks the first one (matches pick_next_task)" {
  run pick_parallel_batch 1
  [ "$output" = "T01" ]
}
