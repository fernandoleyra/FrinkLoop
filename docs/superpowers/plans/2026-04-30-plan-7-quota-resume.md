# FrinkLoop Plan 7 — Quota-Aware Resume (launchd / cron)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** When Claude Code returns a quota-wall error mid-session, FrinkLoop must (1) set `status=quota-stopped` with the reset timestamp, (2) schedule a launchd job (macOS) or cron job (Linux/CCR) to wake the session again at reset+5 minutes, and (3) resume transparently without human intervention. The loop itself stays the same — quota handling is an infrastructure wrapper around it.

**Architecture:** `plugin/lib/quota.sh` detects a quota-hit signal (passed via env or file), writes the reset time to state.json, schedules the wake job, and exits. `plugin/scripts/frinkloop_quota_resume.sh` is what the scheduled job executes — it opens a new Claude Code session pointed at the project's PROMPT.md. The stop hook already handles `status=quota-stopped` by exiting cleanly; this plan wires the schedule-and-resume side.

**Tech Stack:** Bash + `launchctl` (macOS) / `crontab` (Linux). No new npm packages. Cross-platform detection via `uname`.

---

## File Structure

- Create: `plugin/lib/quota.sh`
- Create: `plugin/scripts/frinkloop_quota_resume.sh`
- Modify: `plugin/hooks/stop.sh` — call `schedule_quota_resume` when status=quota-stopped
- Modify: `plugin/commands/frinkloop-resume.md` — document quota-stop resume path
- Create: `tests/plan-7/test_quota.bats`

---

## Task 1: `quota.sh` helpers

**Files:** `plugin/lib/quota.sh`, `tests/plan-7/test_quota.bats`

- [ ] **Step 1: Write failing tests**

`tests/plan-7/test_quota.bats`:

```bash
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
  cancel_scheduled_resume
  [ ! -f "$FRINKLOOP_DIR/scheduled-resume.json" ]
}
```

- [ ] **Step 2: Implement `quota.sh`**

`plugin/lib/quota.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop quota-aware resume helpers.
# Caller must export FRINKLOOP_DIR and source state.sh before sourcing this file.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# quota_hit <reset_iso>  — called when the session detects a quota wall
quota_hit() {
  local reset_at="$1"
  state_set status quota-stopped
  local tmp; tmp=$(mktemp)
  jq --arg r "$reset_at" '. + {quota_reset_at: $r}' "$FRINKLOOP_DIR/state.json" > "$tmp"
  mv "$tmp" "$FRINKLOOP_DIR/state.json"
}

# resume_time_from_reset <reset_iso>  — returns reset + 5 minutes as ISO-8601 UTC
resume_time_from_reset() {
  local reset_at="$1"
  if command -v python3 &>/dev/null; then
    python3 -c "
from datetime import datetime, timedelta, timezone
t = datetime.fromisoformat('${reset_at}'.replace('Z',''))
t = t.replace(tzinfo=timezone.utc) + timedelta(minutes=5)
print(t.strftime('%Y-%m-%dT%H:%M:%SZ'))
"
  else
    # Fallback: use date GNU extension
    date -u -d "${reset_at} + 5 minutes" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null \
      || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" -v +5M "${reset_at}" +"%Y-%m-%dT%H:%M:%SZ"
  fi
}

# schedule_quota_resume <prompt_md_path> <reset_iso>
# Writes a scheduled-resume.json marker file.
# When FRINKLOOP_SKIP_SCHEDULER=1 (tests), skips the OS scheduler call.
schedule_quota_resume() {
  local prompt_path="$1"
  local reset_at="$2"
  local resume_at
  resume_at=$(resume_time_from_reset "$reset_at")

  jq -n \
    --arg prompt "$prompt_path" \
    --arg reset "$reset_at" \
    --arg resume "$resume_at" \
    '{prompt_path: $prompt, reset_at: $reset, resume_at: $resume}' \
    > "$FRINKLOOP_DIR/scheduled-resume.json"

  if [ "${FRINKLOOP_SKIP_SCHEDULER:-0}" = "1" ]; then
    return 0
  fi

  local platform
  platform=$(uname -s)
  case "$platform" in
    Darwin)
      _schedule_launchd "$prompt_path" "$resume_at"
      ;;
    Linux)
      _schedule_cron "$prompt_path" "$resume_at"
      ;;
    *)
      echo "WARN: unsupported platform $platform — manual resume required" >&2
      ;;
  esac
}

_schedule_launchd() {
  local prompt_path="$1"
  local resume_at="$2"
  local label="com.frinkloop.quota-resume"
  local plist="$HOME/Library/LaunchAgents/${label}.plist"
  local resume_script
  resume_script="$(cd "$(dirname "${BASH_SOURCE[0]}")/../scripts" && pwd)/frinkloop_quota_resume.sh"

  # Parse resume_at into year/month/day/hour/minute for StartCalendarInterval
  local yr mo dy hr mi
  yr="${resume_at:0:4}"
  mo="${resume_at:5:2}"
  dy="${resume_at:8:2}"
  hr="${resume_at:11:2}"
  mi="${resume_at:14:2}"

  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${resume_script}</string>
    <string>${prompt_path}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Year</key><integer>${yr#0}</integer>
    <key>Month</key><integer>${mo#0}</integer>
    <key>Day</key><integer>${dy#0}</integer>
    <key>Hour</key><integer>${hr#0}</integer>
    <key>Minute</key><integer>${mi#0}</integer>
  </dict>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PLIST

  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
}

_schedule_cron() {
  local prompt_path="$1"
  local resume_at="$2"
  local resume_script
  resume_script="$(cd "$(dirname "${BASH_SOURCE[0]}")/../scripts" && pwd)/frinkloop_quota_resume.sh"

  local hr mi dy mo
  mi="${resume_at:14:2}"
  hr="${resume_at:11:2}"
  dy="${resume_at:8:2}"
  mo="${resume_at:5:2}"

  local cron_line
  cron_line="${mi#0} ${hr#0} ${dy#0} ${mo#0} * /bin/bash '${resume_script}' '${prompt_path}' # frinkloop-quota-resume"

  # Remove any existing frinkloop-quota-resume entry, then add new one
  ( crontab -l 2>/dev/null | grep -v 'frinkloop-quota-resume'; echo "$cron_line" ) | crontab -
}

# cancel_scheduled_resume — removes the marker file and unloads the OS job
cancel_scheduled_resume() {
  rm -f "$FRINKLOOP_DIR/scheduled-resume.json"

  if [ "${FRINKLOOP_SKIP_SCHEDULER:-0}" = "1" ]; then
    return 0
  fi

  local platform
  platform=$(uname -s)
  case "$platform" in
    Darwin)
      local plist="$HOME/Library/LaunchAgents/com.frinkloop.quota-resume.plist"
      launchctl unload "$plist" 2>/dev/null || true
      rm -f "$plist"
      ;;
    Linux)
      ( crontab -l 2>/dev/null | grep -v 'frinkloop-quota-resume' ) | crontab - 2>/dev/null || true
      ;;
  esac
}
```

- [ ] **Step 3: Run tests, expect PASS**
- [ ] **Step 4: Commit**

---

## Task 2: Resume script + stop hook update

**Files:** `plugin/scripts/frinkloop_quota_resume.sh`, `plugin/hooks/stop.sh`

- [ ] **Step 1: Create the resume script**

`plugin/scripts/frinkloop_quota_resume.sh`:

```bash
#!/usr/bin/env bash
# Called by the scheduled job (launchd/cron) when quota resets.
# Usage: frinkloop_quota_resume.sh <path-to-PROMPT.md>
set -euo pipefail

PROMPT_MD="${1:?PROMPT.md path required}"
PROJECT_DIR="$(dirname "$(dirname "$PROMPT_MD")")"
export PROJECT_DIR
export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"

# Source helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/state.sh"
source "$SCRIPT_DIR/../lib/quota.sh"

# Clear quota-stopped, set running
state_set status running
cancel_scheduled_resume

# Re-open a Claude Code session with the project PROMPT.md
# claude --print is used to pass the prompt content to a new headless session
if command -v claude &>/dev/null; then
  exec claude --print "$(cat "$PROMPT_MD")"
else
  echo "ERROR: claude CLI not found. Install Claude Code and retry." >&2
  exit 1
fi
```

- [ ] **Step 2: Make executable**

```bash
chmod +x plugin/scripts/frinkloop_quota_resume.sh
```

- [ ] **Step 3: Commit**

---

*End of Plan 7.*
