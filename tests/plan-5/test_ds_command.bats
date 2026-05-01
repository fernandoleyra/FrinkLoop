#!/usr/bin/env bats

@test "design-system-builder SKILL.md no longer says 'arrives in Plan 5'" {
  ! grep -q "arrives in Plan 5" plugin/skills/design-system-builder/SKILL.md
}

@test "design-system-builder SKILL.md references all 4 modes" {
  for mode in "use existing" "clone" "create new" "stack default"; do
    grep -qi "$mode" plugin/skills/design-system-builder/SKILL.md
  done
}

@test "frinkloop-ds command no longer says 'arrives in Plan 5'" {
  ! grep -q "arrives in Plan 5" plugin/commands/frinkloop-ds.md
}

@test "frinkloop-ds command documents 4 subcommands" {
  for sub in list new clone push; do
    grep -q "/frinkloop ds $sub" plugin/commands/frinkloop-ds.md
  done
}
