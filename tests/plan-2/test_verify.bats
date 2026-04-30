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
  # Pre-resolve plugin dir from test file location (workaround for cd breaking relative paths)
  export PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  source "$PLUGIN_DIR/lib/verify.sh"
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "verify_task accepts a doc kind without running tests" {
  echo "# README" > README.md
  run verify_task '{"id":"T04","kind":"doc","title":"Write README"}'
  [ "$status" -eq 0 ]
}

@test "verify_task fails when test kind has no tests dir" {
  run verify_task '{"id":"T05","kind":"test","title":"Add tests"}'
  [ "$status" -ne 0 ]
}

@test "verify_task writes a qa-result artifact" {
  echo "# README" > README.md
  verify_task '{"id":"T04","kind":"doc","title":"Write README"}'
  [ -f "$FRINKLOOP_DIR/qa.json" ]
  run jq -r '.task_id' "$FRINKLOOP_DIR/qa.json"
  [ "$output" = "T04" ]
  run jq -r '.outcome' "$FRINKLOOP_DIR/qa.json"
  [ "$output" = "pass" ]
}

@test "qa.json validates against schema" {
  echo "# README" > README.md
  verify_task '{"id":"T04","kind":"doc","title":"Write README"}'
  # Run npx from the repo root where node_modules lives (PLUGIN_DIR/../)
  local repo_root
  repo_root="$(cd "$PLUGIN_DIR/.." && pwd)"
  run bash -c "cd '$repo_root' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/qa-result.schema.json' -d '$FRINKLOOP_DIR/qa.json' --strict=false"
  [ "$status" -eq 0 ]
}
