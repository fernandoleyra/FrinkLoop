#!/usr/bin/env bats

@test "claude-default tokens.json exists and is valid JSON" {
  [ -f plugin/design-systems/claude-default/tokens.json ]
  run jq . plugin/design-systems/claude-default/tokens.json
  [ "$status" -eq 0 ]
}

@test "claude-default tokens.json validates against schema" {
  run npx --no-install ajv validate -s plugin/lib/schemas/design-system-tokens.schema.json -d plugin/design-systems/claude-default/tokens.json --strict=false
  [ "$status" -eq 0 ]
}

@test "claude-default tokens has color, spacing, typography, radii" {
  for k in color spacing typography radii; do
    run jq -r ".$k" plugin/design-systems/claude-default/tokens.json
    [ "$output" != "null" ]
  done
}

@test "claude-default has components.md and README.md" {
  [ -f plugin/design-systems/claude-default/components.md ]
  [ -f plugin/design-systems/claude-default/README.md ]
}
