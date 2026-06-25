#!/usr/bin/env bash
# Called by the scheduled job (launchd/cron) when quota resets.
# Usage: frinkloop_quota_resume.sh <path-to-PROMPT.md>

set -euo pipefail

PROMPT_MD="${1:?PROMPT.md path required}"
PROJECT_DIR="$(dirname "$(dirname "$PROMPT_MD")")"
export PROJECT_DIR
export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/state.sh"
source "$SCRIPT_DIR/../lib/quota.sh"

state_set status running
cancel_scheduled_resume

if command -v claude &>/dev/null; then
  exec claude --print "$(cat "$PROMPT_MD")"
else
  echo "ERROR: claude CLI not found. Install Claude Code and retry." >&2
  exit 1
fi
