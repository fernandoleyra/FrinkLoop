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

@test "mvp-loop SKILL.md is no longer the Plan 1 placeholder" {
  ! grep -q "placeholder — implemented in Plan 2" plugin/skills/mvp-loop/SKILL.md
}

@test "mvp-loop SKILL.md describes the per-iteration steps" {
  grep -q "pick_next_task" plugin/skills/mvp-loop/SKILL.md
  grep -q "verify_task" plugin/skills/mvp-loop/SKILL.md
  grep -q "mark_task_done" plugin/skills/mvp-loop/SKILL.md
  grep -q "queue_fix_task" plugin/skills/mvp-loop/SKILL.md
}

@test "mvp-loop SKILL.md references all 3 subagent roles" {
  grep -q "planner" plugin/skills/mvp-loop/SKILL.md
  grep -q "builder" plugin/skills/mvp-loop/SKILL.md
  grep -q "qa" plugin/skills/mvp-loop/SKILL.md
}

@test "planner agent has real body and references spec.md + tasks.json" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/planner.md
  grep -q "spec.md" plugin/agents/planner.md
  grep -q "tasks.json" plugin/agents/planner.md
}

@test "builder agent has real body and emphasizes commit-per-task" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/builder.md
  grep -q "git commit" plugin/agents/builder.md
}

@test "qa agent has real body and writes qa.json" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/qa.md
  grep -q "qa.json" plugin/agents/qa.md
}
