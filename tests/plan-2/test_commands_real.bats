#!/usr/bin/env bats

@test "frinkloop-resume.md no longer says 'Resume arrives in Plan 2'" {
  ! grep -q "Resume arrives in Plan 2" plugin/commands/frinkloop-resume.md
}

@test "frinkloop-resume.md references state.json validation and recovery.sh" {
  grep -q "state.json" plugin/commands/frinkloop-resume.md
  grep -q "recovery.sh" plugin/commands/frinkloop-resume.md
}

@test "frinkloop-pause.md no longer says 'Pause arrives in Plan 2'" {
  ! grep -q "Pause arrives in Plan 2" plugin/commands/frinkloop-pause.md
}

@test "frinkloop-pause.md sets status to paused and triggers handoff" {
  grep -q "paused" plugin/commands/frinkloop-pause.md
  grep -q "handoff" plugin/commands/frinkloop-pause.md
}
