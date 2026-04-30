#!/usr/bin/env bats

@test "PROMPT.md.tmpl exists and references key state files" {
  [ -f plugin/skills/mvp-loop/PROMPT.md.tmpl ]
  grep -q "state.json" plugin/skills/mvp-loop/PROMPT.md.tmpl
  grep -q "tasks.json" plugin/skills/mvp-loop/PROMPT.md.tmpl
  grep -q "spec.md" plugin/skills/mvp-loop/PROMPT.md.tmpl
  grep -q "PROMPT.md" plugin/skills/mvp-loop/PROMPT.md.tmpl
}

@test "PROMPT.md.tmpl has a DONE marker the Stop hook can recognize" {
  grep -q "DONE" plugin/skills/mvp-loop/PROMPT.md.tmpl
}
