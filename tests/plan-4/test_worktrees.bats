#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"

  export PROJECT_DIR="$TMPDIR/proj"
  mkdir -p "$PROJECT_DIR"
  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t
  echo "init" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "init"
  source "$PLUGIN_LIB_DIR/worktrees.sh"
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "create_task_worktree creates a worktree at the right path" {
  path=$(create_task_worktree T01)
  [ -d "$path" ]
  [ -f "$path/README.md" ]
}

@test "create_task_worktree creates a unique branch frinkloop/task-<id>" {
  create_task_worktree T01 >/dev/null
  run git branch --list 'frinkloop/task-T01'
  [ -n "$output" ]
}

@test "list_task_worktrees returns paths matching the task pattern" {
  create_task_worktree T01 >/dev/null
  create_task_worktree T02 >/dev/null
  run list_task_worktrees
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "frinkloop/task-T01"
  echo "$output" | grep -q "frinkloop/task-T02"
}

@test "remove_task_worktree cleans up cleanly" {
  path=$(create_task_worktree T01)
  remove_task_worktree T01
  [ ! -d "$path" ]
  run git branch --list 'frinkloop/task-T01'
  [ -z "$output" ]
}

@test "prune_task_worktrees removes all task worktrees" {
  create_task_worktree T01 >/dev/null
  create_task_worktree T02 >/dev/null
  prune_task_worktrees
  run list_task_worktrees
  [ -z "$output" ]
}
