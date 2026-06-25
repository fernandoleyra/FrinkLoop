#!/usr/bin/env bats

@test "doc-writer agent no longer has placeholder text" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/doc-writer.md
}

@test "doc-writer agent references spec.md and decisions.md" {
  grep -q "spec.md" plugin/agents/doc-writer.md
  grep -q "decisions.md" plugin/agents/doc-writer.md
}

@test "doc-writer agent specifies README and LANDING.md outputs" {
  grep -q "README.md" plugin/agents/doc-writer.md
  grep -q "LANDING.md" plugin/agents/doc-writer.md
}

@test "screenshot-capturer agent no longer has placeholder text" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/screenshot-capturer.md
}

@test "screenshot-capturer agent references hero and mobile screenshots" {
  grep -q "hero.png" plugin/agents/screenshot-capturer.md
  grep -q "mobile.png" plugin/agents/screenshot-capturer.md
}

@test "screenshot-capturer agent references Playwright" {
  grep -q "playwright\|Playwright" plugin/agents/screenshot-capturer.md
}

@test "frinkloop-deliver command no longer says 'arrives in Plan 8'" {
  ! grep -q "arrives in Plan 8" plugin/commands/frinkloop-deliver.md
}

@test "frinkloop-deliver command documents doc-writer and screenshot-capturer" {
  grep -q "doc-writer" plugin/commands/frinkloop-deliver.md
  grep -q "screenshot-capturer" plugin/commands/frinkloop-deliver.md
}

@test "deliver skill exists with correct frontmatter" {
  [ -f plugin/skills/deliver/SKILL.md ]
  grep -q "deliver" plugin/skills/deliver/SKILL.md
}

@test "deliver skill references all 3 deliverable types" {
  grep -q "README\|docs" plugin/skills/deliver/SKILL.md
  grep -q "screenshot" plugin/skills/deliver/SKILL.md
  grep -q "deploy\|Vercel\|vercel" plugin/skills/deliver/SKILL.md
}
