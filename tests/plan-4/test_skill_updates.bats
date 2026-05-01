#!/usr/bin/env bats

@test "mvp-loop SKILL.md mentions parallel fan-out and pick_parallel_batch" {
  grep -q "pick_parallel_batch" plugin/skills/mvp-loop/SKILL.md
  grep -q -i "parallel" plugin/skills/mvp-loop/SKILL.md
  grep -q "10" plugin/skills/mvp-loop/SKILL.md
}

@test "mvp-loop SKILL.md mentions worktree-per-task" {
  grep -q -i "worktree" plugin/skills/mvp-loop/SKILL.md
  grep -q "create_task_worktree" plugin/skills/mvp-loop/SKILL.md
}

@test "builder agent has worktree contract section" {
  grep -q -i "worktree" plugin/agents/builder.md
  grep -q "PROJECT_DIR" plugin/agents/builder.md
  grep -q "frinkloop/task-" plugin/agents/builder.md
}
