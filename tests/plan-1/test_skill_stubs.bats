#!/usr/bin/env bats

@test "mvp-loop SKILL.md exists with frontmatter" {
  [ -f plugin/skills/mvp-loop/SKILL.md ]
  head -1 plugin/skills/mvp-loop/SKILL.md | grep -q '^---$'
  grep -q '^name:' plugin/skills/mvp-loop/SKILL.md
  grep -q '^description:' plugin/skills/mvp-loop/SKILL.md
}

@test "design-system-builder SKILL.md exists with frontmatter" {
  [ -f plugin/skills/design-system-builder/SKILL.md ]
  head -1 plugin/skills/design-system-builder/SKILL.md | grep -q '^---$'
  grep -q '^name:' plugin/skills/design-system-builder/SKILL.md
  grep -q '^description:' plugin/skills/design-system-builder/SKILL.md
}
