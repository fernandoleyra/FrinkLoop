#!/bin/bash
# git-checkpoint.sh — Commit current state of a project
# Usage: bash git-checkpoint.sh <project-name> "commit message"

PROJECT_NAME="$1"
MESSAGE="$2"
ROOT_DIR="$(dirname "$(dirname "$0")")"
PROJECT_DIR="$ROOT_DIR/projects/$PROJECT_NAME"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "ERROR: project '$PROJECT_NAME' not found"
  exit 1
fi

cd "$PROJECT_DIR"
git add -A
git commit -m "$MESSAGE" || echo "Nothing to commit"
echo "Checkpoint saved: $MESSAGE"
