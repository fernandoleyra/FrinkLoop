#!/usr/bin/env bats

setup() {
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  export PLUGIN_DIR
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  source "$PLUGIN_DIR/lib/caveman.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "caveman_prefix none returns prompt unchanged" {
  result=$(caveman_prefix none "do the thing")
  [ "$result" = "do the thing" ]
}

@test "caveman_prefix empty string returns prompt unchanged" {
  result=$(caveman_prefix "" "hello world")
  [ "$result" = "hello world" ]
}

@test "caveman_prefix lite prepends terse directive" {
  result=$(caveman_prefix lite "build the feature")
  echo "$result" | grep -q "COMPRESS"
  echo "$result" | grep -q "build the feature"
}

@test "caveman_prefix full prepends caveman directive" {
  result=$(caveman_prefix full "implement login form")
  echo "$result" | grep -qi "CAVEMAN"
  echo "$result" | grep -q "implement login form"
}

@test "caveman_prefix ultra prepends ultra directive" {
  result=$(caveman_prefix ultra "add button")
  echo "$result" | grep -qi "ULTRA"
  echo "$result" | grep -q "add button"
}

@test "caveman_prefix unknown level returns prompt unchanged" {
  result=$(caveman_prefix bogus "test prompt")
  [ "$result" = "test prompt" ]
}

@test "read_compression_level returns none when no config.yaml" {
  run read_compression_level "/nonexistent/config.yaml"
  [ "$output" = "none" ]
}

@test "read_compression_level reads from config.yaml" {
  printf 'compression: full\n' > "$FRINKLOOP_DIR/config.yaml"
  run read_compression_level "$FRINKLOOP_DIR/config.yaml"
  [ "$output" = "full" ]
}

@test "plugin.json version is 0.9.0" {
  run jq -r '.version' "$PLUGIN_DIR/plugin.json"
  [ "$output" = "0.9.0" ]
}

@test "plugin README has Acknowledgements section" {
  grep -q "Acknowledgements\|acknowledgements" "$PLUGIN_DIR/README.md"
}

@test "plugin README acknowledges Ralph Loop" {
  grep -q -i "ralph\|Ralph" "$PLUGIN_DIR/README.md"
}

@test "mvp-loop SKILL.md has concrete caveman dispatch example" {
  grep -q "caveman_prefix" "$PLUGIN_DIR/skills/mvp-loop/SKILL.md"
  grep -q "read_compression_level" "$PLUGIN_DIR/skills/mvp-loop/SKILL.md"
}

@test "stop hook exit 2 convention is documented" {
  grep -q "exit 2" "$PLUGIN_DIR/hooks/stop.sh"
}
