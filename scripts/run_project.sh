#!/bin/bash
# ─────────────────────────────────────────────────────────────
# run_project.sh — Start or resume the agent loop for a project
#
# Usage:
#   ./run_project.sh <project-name>
#   ./run_project.sh <project-name> --dry-run
# ─────────────────────────────────────────────────────────────

set -e

PROJECT_NAME=${1:-""}
DRY_RUN=${2:-""}
AGENT_OS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$PROJECT_NAME" ]; then
  echo "Usage: ./run_project.sh <project-name> [--dry-run]"
  echo ""
  echo "Active projects:"
  ls "$AGENT_OS_ROOT/projects/" 2>/dev/null || echo "  (none yet)"
  exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "Error: ANTHROPIC_API_KEY is not set."
  exit 1
fi

PROJECT_PATH="$AGENT_OS_ROOT/projects/$PROJECT_NAME"

if [ ! -d "$PROJECT_PATH" ]; then
  echo "Project not found: $PROJECT_PATH"
  echo "Create it first: ./scripts/new_project.sh $PROJECT_NAME"
  exit 1
fi

if [ ! -f "$PROJECT_PATH/BRIEF.md" ]; then
  echo "No BRIEF.md found in $PROJECT_PATH"
  echo "Create a BRIEF.md describing what to build, then run again."
  exit 1
fi

# Check if BRIEF.md is still the template
if grep -q "Describe what you want built" "$PROJECT_PATH/BRIEF.md"; then
  echo "BRIEF.md appears to be unfilled. Please edit it before running."
  echo "File: $PROJECT_PATH/BRIEF.md"
  exit 1
fi

echo ""
echo "════════════════════════════════════════════"
echo "  Agent OS — Starting"
echo "  Project: $PROJECT_NAME"
echo "  Path: $PROJECT_PATH"
echo "════════════════════════════════════════════"
echo ""

# Load .env if present
if [ -f "$AGENT_OS_ROOT/.env" ]; then
  echo "Loading environment from .env..."
  export $(cat "$AGENT_OS_ROOT/.env" | grep -v '^#' | xargs)
fi

# Run the loop
cd "$AGENT_OS_ROOT"

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "Running in DRY RUN mode — no API calls will be made"
  python -m core.loop --project "$PROJECT_NAME" --dry-run
else
  python -m core.loop --project "$PROJECT_NAME"
fi
