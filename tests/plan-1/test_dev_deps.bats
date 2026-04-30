#!/usr/bin/env bats

@test "package.json exists and lists test deps" {
  [ -f package.json ]
  run jq -r '.devDependencies."ajv-cli"' package.json
  [ "$status" -eq 0 ]
  [ "$output" != "null" ]
}

@test "ajv-cli is callable" {
  run npx --no-install ajv help
  [ "$status" -eq 0 ]
}

@test "bats is callable" {
  run bats --version
  [ "$status" -eq 0 ]
}
