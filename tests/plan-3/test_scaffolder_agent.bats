#!/usr/bin/env bats

@test "scaffolder agent has real body and references registry + giget + recipes" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/scaffolder.md
  grep -q "registry.yaml" plugin/agents/scaffolder.md
  grep -q "giget" plugin/agents/scaffolder.md
  grep -q "apply_recipe" plugin/agents/scaffolder.md
}
