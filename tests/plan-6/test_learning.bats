#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  export PROJECT_DIR="$TMPDIR/proj"
  mkdir -p "$FRINKLOOP_DIR" "$PROJECT_DIR"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  export PLUGIN_DIR
  source "$PLUGIN_DIR/lib/learning.sh"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "emit_event writes a JSONL line to events.jsonl" {
  emit_event task_done myproject T01 feature 5
  [ -f "$FRINKLOOP_DIR/events.jsonl" ]
  run jq -r '.event' "$FRINKLOOP_DIR/events.jsonl"
  [ "$output" = "task_done" ]
}

@test "emit_event appends multiple events" {
  emit_event task_done myproject T01 feature 3
  emit_event qa_pass   myproject T01 feature 1
  run wc -l < "$FRINKLOOP_DIR/events.jsonl"
  [ "$output" -eq 2 ]
}

@test "emit_event produces valid JSON on each line" {
  emit_event task_failed myproject T02 fix 10
  run jq -r '.event' "$FRINKLOOP_DIR/events.jsonl"
  [ "$status" -eq 0 ]
  [ "$output" = "task_failed" ]
}

@test "profile_init creates profile.json with zero stats" {
  profile_init myproject
  [ -f "$FRINKLOOP_DIR/profile.json" ]
  run jq -r '.project' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "myproject" ]
  run jq -r '.task_stats.total' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "0" ]
}

@test "profile_increment increments the given task_stats counter" {
  profile_init myproject
  profile_increment done
  profile_increment done
  profile_increment failed
  run jq -r '.task_stats.done' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
  run jq -r '.task_stats.failed' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "1" ]
}

@test "profile_set_template records template_used" {
  profile_init myproject
  profile_set_template vite-shadcn
  run jq -r '.template_used' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "vite-shadcn" ]
}

@test "profile_add_recipe appends to recipes_applied" {
  profile_init myproject
  profile_add_recipe tailwind
  profile_add_recipe playwright
  run jq -r '.recipes_applied | length' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
}

@test "profile_set_qa_rate stores qa_pass_rate" {
  profile_init myproject
  profile_set_qa_rate 0.85
  run jq -r '.qa_pass_rate' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "0.85" ]
}

@test "profile.json validates against schema" {
  profile_init myproject
  run npx --no-install ajv validate \
    -s "$PLUGIN_DIR/lib/schemas/profile.schema.json" \
    -d "$FRINKLOOP_DIR/profile.json" --strict=false
  [ "$status" -eq 0 ]
}
