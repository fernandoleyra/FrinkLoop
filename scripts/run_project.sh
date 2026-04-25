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
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

if [ -z "$PROJECT_NAME" ]; then
  echo "Usage: ./run_project.sh <project-name> [--dry-run]"
  echo ""
  echo "Active projects:"
  find "$ROOT_DIR/projects" -mindepth 1 -maxdepth 1 -type d -not -name "_template" -exec basename {} \; 2>/dev/null || echo "  (none yet)"
  exit 1
fi

PROJECT_PATH="$ROOT_DIR/projects/$PROJECT_NAME"

if [ ! -d "$PROJECT_PATH" ]; then
  echo "Project not found: $PROJECT_PATH"
  echo "Create it first: $PYTHON_BIN frinkloop.py new $PROJECT_NAME"
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
echo "  FrinkLoop — Starting"
echo "  Project: $PROJECT_NAME"
echo "  Path: $PROJECT_PATH"
echo "════════════════════════════════════════════"
echo ""

# Load .env if present
if [ -f "$ROOT_DIR/.env" ]; then
  echo "Loading environment from .env..."
  set -a
  . "$ROOT_DIR/.env"
  set +a
fi

# Run the loop
cd "$ROOT_DIR"

if [ "$DRY_RUN" = "--dry-run" ]; then
  echo "Running in DRY RUN mode — no API calls will be made"
  "$PYTHON_BIN" frinkloop.py run "$PROJECT_NAME" --dry-run
else
  "$PYTHON_BIN" frinkloop.py run "$PROJECT_NAME"
fi
