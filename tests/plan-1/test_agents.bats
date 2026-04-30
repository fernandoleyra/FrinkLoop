#!/usr/bin/env bats

@test "all 6 agent role files exist with frontmatter" {
  for a in planner scaffolder builder qa doc-writer screenshot-capturer; do
    [ -f "plugin/agents/$a.md" ] || (echo "missing $a.md" && false)
    head -1 "plugin/agents/$a.md" | grep -q '^---$' || (echo "no frontmatter in $a" && false)
    grep -q '^name:' "plugin/agents/$a.md" || (echo "no name in $a" && false)
    grep -q '^description:' "plugin/agents/$a.md" || (echo "no description in $a" && false)
  done
}
