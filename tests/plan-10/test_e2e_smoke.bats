#!/usr/bin/env bats
# Plan 10 — End-to-end smoke test (Vite+shadcn hackathon run)
# Exercises the full pipeline without calling Claude.
# Each @test corresponds to one logical pipeline stage.

PLUGIN_DIR_ABS="$(cd "$(dirname "$BATS_TEST_FILENAME")/../../plugin" && pwd)"
FIXTURE_DIR="$(dirname "$BATS_TEST_FILENAME")/fixtures"

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/vite-shadcn-todo"
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  export PLUGIN_DIR="$PLUGIN_DIR_ABS"

  # Init a real git repo so verify_task / recovery helpers work
  cd "$PROJECT_DIR"
  git init -q
  git config user.email "smoke@frinkloop.test"
  git config user.name "Smoke"

  # Source all Plan 1-9 libs
  source "$PLUGIN_DIR/lib/state.sh"
  source "$PLUGIN_DIR/lib/loop.sh"
  source "$PLUGIN_DIR/lib/verify.sh"
  source "$PLUGIN_DIR/lib/recovery.sh"
  source "$PLUGIN_DIR/lib/learning.sh"
  source "$PLUGIN_DIR/lib/quota.sh"
  source "$PLUGIN_DIR/lib/caveman.sh"

  # Seed state + tasks from fixture
  state_init main
  state_set status running
  cp "$FIXTURE_DIR/vite-shadcn-tasks.json" "$FRINKLOOP_DIR/tasks.json"
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

# ---------------------------------------------------------------------------
# Plan 1 — state helpers
# ---------------------------------------------------------------------------

@test "[plan-1] state_init creates a valid state.json" {
  [ -f "$FRINKLOOP_DIR/state.json" ]
  run jq -r '.status' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "running" ]
}

@test "[plan-1] state_set and state_get round-trip" {
  state_set current_milestone m1
  run state_get current_milestone
  [ "$output" = "m1" ]
}

# ---------------------------------------------------------------------------
# Plan 2 — loop core
# ---------------------------------------------------------------------------

@test "[plan-2] pick_next_task returns T02 (first pending in m1)" {
  run pick_next_task
  [ "$output" = "T02" ]
}

@test "[plan-2] pick_next_task respects depends_on (T03 blocked by T02)" {
  run pick_next_task
  [ "$output" != "T03" ]
}

@test "[plan-2] stub builder: write file + commit, then verify_task passes for doc kind" {
  # Simulate builder doing work for T02 (scaffold kind — lightweight verify)
  echo "# Vite+shadcn README" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "scaffold: bootstrap"

  task_json='{"id":"T02","title":"Apply tailwind recipe","status":"pending","kind":"scaffold"}'
  run verify_task "$task_json"
  [ "$status" -eq 0 ]
  [ -f "$FRINKLOOP_DIR/qa.json" ]
  run jq -r '.outcome' "$FRINKLOOP_DIR/qa.json"
  [ "$output" = "pass" ]
}

@test "[plan-2] mark_task_done updates tasks.json and appends decisions.md" {
  mark_task_done T02 "Applied tailwind via recipe"
  run jq -r '.milestones[0].tasks[1].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]
  [ -f "$FRINKLOOP_DIR/decisions.md" ]
  grep -q "T02" "$FRINKLOOP_DIR/decisions.md"
}

@test "[plan-2] queue_fix_task adds a fix task after T03" {
  queue_fix_task T03 "tailwind config missing"
  run jq -r '.milestones[0].tasks | length' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" -eq 4 ]
  run jq -r '.milestones[0].tasks[3].kind' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "fix" ]
}

@test "[plan-2] stop hook exits 2 when status=running and tasks pending" {
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 2 ]
}

@test "[plan-2] stop hook exits 0 when status=done" {
  state_set status done
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 0 ]
}

@test "[plan-2] post-iteration hook increments iteration_count" {
  run "$PLUGIN_DIR/hooks/post-iteration.sh"
  [ "$status" -eq 0 ]
  run jq -r '.iteration_count' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "1" ]
}

# ---------------------------------------------------------------------------
# Plan 3 — templates registry
# ---------------------------------------------------------------------------

@test "[plan-3] registry.yaml exists and is valid YAML" {
  [ -f "$PLUGIN_DIR/templates/registry.yaml" ]
  run yq '.' "$PLUGIN_DIR/templates/registry.yaml"
  [ "$status" -eq 0 ]
}

@test "[plan-3] registry includes vite-shadcn template" {
  run yq -r '.templates[] | select(.id == "vite-shadcn") | .id' "$PLUGIN_DIR/templates/registry.yaml"
  [ "$output" = "vite-shadcn" ]
}

# ---------------------------------------------------------------------------
# Plan 4 — parallel helpers
# ---------------------------------------------------------------------------

@test "[plan-4] worktrees.sh exists and exports pick_parallel_batch" {
  [ -f "$PLUGIN_DIR/lib/worktrees.sh" ]
  source "$PLUGIN_DIR/lib/worktrees.sh"
  declare -f pick_parallel_batch > /dev/null
}

# ---------------------------------------------------------------------------
# Plan 5 — design system store
# ---------------------------------------------------------------------------

@test "[plan-5] claude-default design system exists with tokens.json" {
  [ -f "$PLUGIN_DIR/design-systems/claude-default/tokens.json" ]
  run jq -r '.color' "$PLUGIN_DIR/design-systems/claude-default/tokens.json"
  [ "$output" != "null" ]
}

@test "[plan-5] ds_list helper is available from design_systems.sh" {
  source "$PLUGIN_DIR/lib/design_systems.sh"
  declare -f ds_list > /dev/null
}

# ---------------------------------------------------------------------------
# Plan 6 — local learning
# ---------------------------------------------------------------------------

@test "[plan-6] emit_event writes to events.jsonl" {
  profile_init vite-shadcn-todo
  emit_event task_done vite-shadcn-todo T02 scaffold 4
  [ -f "$FRINKLOOP_DIR/events.jsonl" ]
  run jq -r '.event' "$FRINKLOOP_DIR/events.jsonl"
  [ "$output" = "task_done" ]
}

@test "[plan-6] profile_increment done tracks completed tasks" {
  profile_init vite-shadcn-todo
  profile_increment done
  profile_increment done
  run jq -r '.task_stats.done' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
}

# ---------------------------------------------------------------------------
# Plan 7 — quota-aware resume
# ---------------------------------------------------------------------------

@test "[plan-7] quota_hit sets status quota-stopped and records reset time" {
  quota_hit "2026-05-02T12:00:00Z"
  run jq -r '.status' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "quota-stopped" ]
  run jq -r '.quota_reset_at' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "2026-05-02T12:00:00Z" ]
}

@test "[plan-7] resume_time_from_reset is exactly reset + 5 min" {
  run resume_time_from_reset "2026-05-02T12:00:00Z"
  [ "$output" = "2026-05-02T12:05:00Z" ]
}

@test "[plan-7] schedule_quota_resume writes scheduled-resume.json (skip OS scheduler)" {
  quota_hit "2026-05-02T12:00:00Z"
  FRINKLOOP_SKIP_SCHEDULER=1 schedule_quota_resume "$FRINKLOOP_DIR/PROMPT.md" "2026-05-02T12:00:00Z"
  [ -f "$FRINKLOOP_DIR/scheduled-resume.json" ]
}

# ---------------------------------------------------------------------------
# Plan 8 — deliverables
# ---------------------------------------------------------------------------

@test "[plan-8] doc-writer agent file has real body (no placeholder)" {
  ! grep -q "Placeholder" "$PLUGIN_DIR/agents/doc-writer.md"
  grep -q "README.md" "$PLUGIN_DIR/agents/doc-writer.md"
}

@test "[plan-8] screenshot-capturer agent file has real body" {
  ! grep -q "Placeholder" "$PLUGIN_DIR/agents/screenshot-capturer.md"
  grep -q "hero.png" "$PLUGIN_DIR/agents/screenshot-capturer.md"
}

@test "[plan-8] deliver SKILL.md exists and covers 3 deliverable types" {
  [ -f "$PLUGIN_DIR/skills/deliver/SKILL.md" ]
  grep -q "README\|docs" "$PLUGIN_DIR/skills/deliver/SKILL.md"
  grep -q "screenshot" "$PLUGIN_DIR/skills/deliver/SKILL.md"
  grep -q "deploy\|vercel\|Vercel" "$PLUGIN_DIR/skills/deliver/SKILL.md"
}

# ---------------------------------------------------------------------------
# Plan 9 — caveman compression
# ---------------------------------------------------------------------------

@test "[plan-9] caveman_prefix lite wraps prompt with terse directive" {
  result=$(caveman_prefix lite "implement the login page")
  echo "$result" | grep -q "COMPRESS"
}

@test "[plan-9] caveman_prefix none returns prompt unchanged" {
  result=$(caveman_prefix none "build the thing")
  [ "$result" = "build the thing" ]
}

@test "[plan-9] plugin.json version is 0.9.0" {
  run jq -r '.version' "$PLUGIN_DIR/plugin.json"
  [ "$output" = "0.9.0" ]
}

# ---------------------------------------------------------------------------
# Full iteration walkthrough
# ---------------------------------------------------------------------------

@test "[e2e] one complete iteration: pick → stub-build → verify → mark-done → learning → hook" {
  # 1. pick
  task_id=$(pick_next_task)
  [ "$task_id" = "T02" ]

  # 2. stub builder: commit a file
  echo "tailwind config" > tailwind.config.ts
  git add tailwind.config.ts
  git -c commit.gpgsign=false commit -q -m "scaffold(tailwind): apply recipe"

  # 3. verify
  task_json=$(jq --arg tid "$task_id" '.milestones[].tasks[] | select(.id==$tid)' "$FRINKLOOP_DIR/tasks.json")
  run verify_task "$task_json"
  [ "$status" -eq 0 ]

  # 4. mark done
  mark_task_done "$task_id" "Tailwind recipe applied"
  run jq -r '.milestones[0].tasks[1].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]

  # 5. learning event
  profile_init vite-shadcn-todo
  emit_event task_done vite-shadcn-todo "$task_id" scaffold 3
  profile_increment done
  run jq -r '.task_stats.done' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "1" ]

  # 6. post-iteration hook
  run "$PLUGIN_DIR/hooks/post-iteration.sh"
  [ "$status" -eq 0 ]
  run jq -r '.iteration_count' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "1" ]

  # 7. stop hook still loops (T03 still pending)
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 2 ]
}
