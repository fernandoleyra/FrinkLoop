#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/proj"
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t
  # Create .gitkeep so .frinkloop/ is tracked and tree stays clean
  touch "$FRINKLOOP_DIR/.gitkeep"
  echo "# initial" > README.md
  git add .frinkloop README.md
  git -c commit.gpgsign=false commit -q -m "init"
  # Pre-resolve plugin dir from test file location (workaround for cd breaking relative paths)
  export PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  source "$PLUGIN_LIB_DIR/state.sh"
  # Create state.json and add it to git so tree stays clean
  state_init main
  git add "$FRINKLOOP_DIR/state.json"
  git -c commit.gpgsign=false commit -q -m "init state"
  source "$PLUGIN_LIB_DIR/recovery.sh"
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "detect_dirty_tree returns 0 when working tree is clean" {
  run detect_dirty_tree
  [ "$status" -eq 0 ]
}

@test "detect_dirty_tree returns 1 when working tree has unstaged changes" {
  echo "modified" >> README.md
  run detect_dirty_tree
  [ "$status" -eq 1 ]
}

@test "open_blocker writes blockers.md entry" {
  open_blocker "T03" "user manually edited working tree mid-loop"
  [ -f "$FRINKLOOP_DIR/blockers.md" ]
  grep -q "T03" "$FRINKLOOP_DIR/blockers.md"
  grep -q "user manually edited" "$FRINKLOOP_DIR/blockers.md"
}

@test "resume_or_block returns 'resume' on clean tree" {
  run resume_or_block
  [ "$output" = "resume" ]
}

@test "resume_or_block returns 'block' on dirty tree and writes blockers.md" {
  echo "wat" > extra.md
  git add extra.md
  run resume_or_block
  [ "$output" = "block" ]
  [ -f "$FRINKLOOP_DIR/blockers.md" ]
}
