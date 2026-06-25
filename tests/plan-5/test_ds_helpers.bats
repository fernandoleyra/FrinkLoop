#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  source "$PLUGIN_LIB_DIR/design_systems.sh"
  export DS_ROOT="$TMPDIR/ds"
  mkdir -p "$DS_ROOT"
  cp -R "$PLUGIN_DIR/design-systems/claude-default" "$DS_ROOT/claude-default"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "ds_list returns the names of stored design systems" {
  run ds_list
  echo "$output" | grep -q "claude-default"
}

@test "ds_get returns the path to the named DS" {
  run ds_get claude-default
  [ "$status" -eq 0 ]
  [ -d "$output" ]
  [ -f "$output/tokens.json" ]
}

@test "ds_get returns nonzero for unknown DS" {
  run ds_get nonexistent
  [ "$status" -ne 0 ]
}

@test "ds_create scaffolds a new DS from the claude-default template" {
  ds_create my-brand "A custom brand"
  [ -d "$DS_ROOT/my-brand" ]
  [ -f "$DS_ROOT/my-brand/tokens.json" ]
  run jq -r '.name' "$DS_ROOT/my-brand/tokens.json"
  [ "$output" = "my-brand" ]
}

@test "ds_clone records the source URL in clone-source.txt" {
  ds_clone https://example.com/brand my-clone
  [ -d "$DS_ROOT/my-clone" ]
  [ -f "$DS_ROOT/my-clone/clone-source.txt" ]
  grep -q "example.com" "$DS_ROOT/my-clone/clone-source.txt"
}
