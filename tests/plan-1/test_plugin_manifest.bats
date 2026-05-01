#!/usr/bin/env bats

@test "plugin.json exists and is valid JSON" {
  [ -f plugin/.claude-plugin/plugin.json ]
  run jq . plugin/.claude-plugin/plugin.json
  [ "$status" -eq 0 ]
}

@test "plugin.json has required fields" {
  run jq -r '.name' plugin/.claude-plugin/plugin.json
  [ "$output" = "frinkloop" ]

  run jq -r '.version' plugin/.claude-plugin/plugin.json
  [ "$status" -eq 0 ]
  [ -n "$output" ]

  run jq -r '.description' plugin/.claude-plugin/plugin.json
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "plugin dir layout exists" {
  for d in commands skills agents hooks lib lib/schemas templates recipes design-systems scripts; do
    [ -d "plugin/$d" ] || (echo "missing plugin/$d" && false)
  done
}
