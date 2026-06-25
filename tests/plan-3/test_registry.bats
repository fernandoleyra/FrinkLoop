#!/usr/bin/env bats

@test "registry.yaml exists and parses to JSON" {
  [ -f plugin/templates/registry.yaml ]
  run yq -o=json plugin/templates/registry.yaml
  [ "$status" -eq 0 ]
}

@test "registry validates against schema" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run npx --no-install ajv validate -s plugin/lib/schemas/registry.schema.json -d /tmp/registry.json --strict=false
  [ "$status" -eq 0 ]
}

@test "registry has 10 entries with required fields" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run jq '.templates | length' /tmp/registry.json
  [ "$output" -ge 10 ]
}

@test "every template entry has a giget source string" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run jq -r '.templates | map(select(.giget == null or .giget == "")) | length' /tmp/registry.json
  [ "$output" = "0" ]
}

@test "registry resolves vite-shadcn template" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run jq -r '.templates[] | select(.id == "vite-shadcn") | .giget' /tmp/registry.json
  [ -n "$output" ]
  [ "$output" != "null" ]
}
