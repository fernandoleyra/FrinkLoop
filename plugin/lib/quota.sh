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
