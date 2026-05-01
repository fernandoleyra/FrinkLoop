#!/usr/bin/env bash
# FrinkLoop worktree manager — per-task isolation for parallel builders.
# Caller's cwd must be a git repo (the project being built). Worktrees live under
# <project>/.frinkloop/worktrees/task-<id>/ branched from current HEAD.

set -euo pipefail

WORKTREE_BASE=".frinkloop/worktrees"

create_task_worktree() {
  local task_id="$1"
  local branch="frinkloop/task-${task_id}"
  local path="$WORKTREE_BASE/task-${task_id}"
  if git worktree list --porcelain | grep -q "$path$"; then
    echo "$(pwd)/$path"
    return 0
  fi
  git worktree add "$path" -b "$branch" >/dev/null
  echo "$(pwd)/$path"
}

remove_task_worktree() {
  local task_id="$1"
  local branch="frinkloop/task-${task_id}"
  local path="$WORKTREE_BASE/task-${task_id}"
  if [ -d "$path" ]; then
    git worktree remove --force "$path" >/dev/null 2>&1 || true
  fi
  git branch -D "$branch" >/dev/null 2>&1 || true
}

list_task_worktrees() {
  git worktree list --porcelain | awk '
    /^worktree / { wt=$2 }
    /^branch refs\/heads\/frinkloop\/task-/ {
      branch=substr($2, length("refs/heads/") + 1)
      print wt " " branch
    }
  '
}

prune_task_worktrees() {
  local paths
  paths=$(list_task_worktrees)
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    # Each line is "<worktree_path> frinkloop/task-<id>"
    local branch="${p##* }"
    local task_id="${branch##*/task-}"
    remove_task_worktree "$task_id"
  done <<< "$paths"
}
