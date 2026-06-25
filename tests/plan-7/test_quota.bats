#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  export PLUGIN_DIR
  source "$PLUGIN_DIR/lib/state.sh"
  state_init main
  source "$PLUGIN_DIR/lib/quota.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "quota_hit sets status to quota-stopped" {
  quota_hit "2026-05-02T10:00:00Z"
  run jq -r '.status' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "quota-stopped" ]
}

@test "quota_hit records quota_reset_at in state.json" {
  quota_hit "2026-05-02T10:00:00Z"
  run jq -r '.quota_reset_at' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "2026-05-02T10:00:00Z" ]
}

@test "resume_time_from_reset adds 5 minutes to reset ISO timestamp" {
  run resume_time_from_reset "2026-05-02T10:00:00Z"
  [ "$status" -eq 0 ]
  [ "$output" = "2026-05-02T10:05:00Z" ]
}

@test "schedule_quota_resume writes a schedule marker file" {
  quota_hit "2026-05-02T10:00:00Z"
  FRINKLOOP_SKIP_SCHEDULER=1 schedule_quota_resume "$FRINKLOOP_DIR/PROMPT.md" "2026-05-02T10:00:00Z"
  [ -f "$FRINKLOOP_DIR/scheduled-resume.json" ]
}

@test "schedule marker contains project path and resume time" {
  quota_hit "2026-05-02T10:00:00Z"
  FRINKLOOP_SKIP_SCHEDULER=1 schedule_quota_resume "$FRINKLOOP_DIR/PROMPT.md" "2026-05-02T10:00:00Z"
  run jq -r '.resume_at' "$FRINKLOOP_DIR/scheduled-resume.json"
  [ "$output" = "2026-05-02T10:05:00Z" ]
}

@test "cancel_scheduled_resume removes the schedule marker" {
  quota_hit "2026-05-02T10:00:00Z"
  FRINKLOOP_SKIP_SCHEDULER=1 schedule_quota_resume "$FRINKLOOP_DIR/PROMPT.md" "2026-05-02T10:00:00Z"
  FRINKLOOP_SKIP_SCHEDULER=1 cancel_scheduled_resume
  [ ! -f "$FRINKLOOP_DIR/scheduled-resume.json" ]
}

@test "stop hook exits 0 when status is quota-stopped" {
  state_set status quota-stopped
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 0 ]
}

@test "frinkloop_quota_resume.sh exists and is executable" {
  [ -x "$PLUGIN_DIR/scripts/frinkloop_quota_resume.sh" ]
}
