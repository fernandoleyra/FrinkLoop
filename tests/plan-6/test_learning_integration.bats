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

teardown() { rm -rf "$TMPDIR"; }

@test "full profile lifecycle: init, set template, add recipe, increment, qa rate" {
  profile_init myproject
  profile_set_template vite-shadcn
  profile_add_recipe tailwind
  profile_add_recipe playwright
  profile_increment done
  profile_increment done
  profile_increment failed
  profile_set_qa_rate 0.67
  profile_milestone_done

  run jq -r '.template_used' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "vite-shadcn" ]
  run jq -r '.recipes_applied | length' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
  run jq -r '.task_stats.done' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
  run jq -r '.milestones_completed' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "1" ]
}

@test "consolidate_profiles merges multiple project profiles" {
  local global_dir="$TMPDIR/projects"
  mkdir -p "$global_dir/proj-a" "$global_dir/proj-b"

  jq -n '{schema_version:1,project:"a",created_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z",template_used:"vite-shadcn",recipes_applied:["tailwind"],task_stats:{total:5,done:5,failed:0,retried:0},qa_pass_rate:1.0,blockers:0,milestones_completed:2,total_duration_s:120}' \
    > "$global_dir/proj-a/profile.json"

  jq -n '{schema_version:1,project:"b",created_at:"2026-01-02T00:00:00Z",updated_at:"2026-01-02T00:00:00Z",template_used:"vite-shadcn",recipes_applied:["playwright"],task_stats:{total:3,done:2,failed:1,retried:1},qa_pass_rate:0.5,blockers:1,milestones_completed:1,total_duration_s:60}' \
    > "$global_dir/proj-b/profile.json"

  consolidate_profiles "$global_dir"
  [ -f "$TMPDIR/global-profile.json" ]

  run jq -r '.project_count' "$TMPDIR/global-profile.json"
  [ "$output" = "2" ]
  run jq -r '.top_templates[0].template' "$TMPDIR/global-profile.json"
  [ "$output" = "vite-shadcn" ]
}

@test "mvp-loop SKILL.md references Plan 6 learning" {
  grep -q "learning" "$PLUGIN_DIR/skills/mvp-loop/SKILL.md"
}
