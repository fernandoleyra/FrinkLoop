#!/bin/bash
# new-project.sh — Initialize a new project in FrinkLoop
# Usage: bash new-project.sh <project-name> "short description"

set -e

PROJECT_NAME="$1"
DESCRIPTION="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$ROOT_DIR/projects/$PROJECT_NAME"
TEMPLATE_DIR="$ROOT_DIR/projects/_template"

if [ -z "$PROJECT_NAME" ]; then
  echo "ERROR: project name required"
  echo "Usage: bash new-project.sh <project-name> 'description'"
  exit 1
fi

if [ -d "$PROJECT_DIR" ]; then
  echo "ERROR: project '$PROJECT_NAME' already exists at $PROJECT_DIR"
  exit 1
fi

echo "Creating project: $PROJECT_NAME"
echo "Description: $DESCRIPTION"

# Copy template
cp -r "$TEMPLATE_DIR" "$PROJECT_DIR"

# Replace placeholders in template files
find "$PROJECT_DIR" -type f | while read f; do
  sed -i "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" "$f" 2>/dev/null || true
  sed -i "s/{{DESCRIPTION}}/$DESCRIPTION/g" "$f" 2>/dev/null || true
  sed -i "s/{{DATE}}/$(date -u +%Y-%m-%dT%H:%M:%SZ)/g" "$f" 2>/dev/null || true
done

# Initialize git
cd "$PROJECT_DIR"
git init -q
git add .
git commit -q -m "chore: initialize project from FrinkLoop template"

# Update memory/state.json
cat > "$ROOT_DIR/memory/state.json" << STATEOF
{
  "project": "$PROJECT_NAME",
  "project_path": "$PROJECT_DIR",
  "phase": "planning",
  "milestone_current": null,
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_activity": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "notes": "$DESCRIPTION"
}
STATEOF

# Update memory/tasks.json with empty project
cat > "$ROOT_DIR/memory/tasks.json" << TASKEOF
{
  "project": "$PROJECT_NAME",
  "milestone_current": null,
  "milestones": [],
  "tasks": [],
  "_instructions": "Orchestrator: populate milestones and tasks based on project spec before starting the main loop"
}
TASKEOF

# Append to decisions log
echo "" >> "$ROOT_DIR/memory/decisions.md"
echo "## PROJECT START | $PROJECT_NAME | $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ROOT_DIR/memory/decisions.md"
echo "Description: $DESCRIPTION" >> "$ROOT_DIR/memory/decisions.md"
echo "Path: $PROJECT_DIR" >> "$ROOT_DIR/memory/decisions.md"

echo ""
echo "Project '$PROJECT_NAME' created at: $PROJECT_DIR"
echo "Next step: Orchestrator reads CLAUDE.md and begins planning phase"
