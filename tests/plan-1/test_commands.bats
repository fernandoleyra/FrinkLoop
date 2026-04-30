#!/usr/bin/env bats

@test "all 7 command files exist" {
  for c in frinkloop frinkloop-new frinkloop-resume frinkloop-status frinkloop-pause frinkloop-ds frinkloop-deliver; do
    [ -f "plugin/commands/$c.md" ] || (echo "missing $c.md" && false)
  done
}

@test "each command file has YAML frontmatter with description" {
  for c in plugin/commands/frinkloop*.md; do
    head -1 "$c" | grep -q '^---$' || (echo "no frontmatter in $c" && false)
    grep -q '^description:' "$c" || (echo "no description in $c" && false)
  done
}

@test "frinkloop-new references the intake-chat skill" {
  grep -q "intake-chat" plugin/commands/frinkloop-new.md
}
