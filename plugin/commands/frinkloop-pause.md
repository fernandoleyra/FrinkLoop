---
description: Pause a running FrinkLoop loop, flush state, write a handoff.
---

# /frinkloop pause <project>

Pause the build loop for `<project>`.

## Steps

1. Resolve `<project>` and export `FRINKLOOP_DIR`, `PROJECT_DIR` as in resume.
2. Source `plugin/lib/state.sh`.
3. `state_set status paused`.
4. `log_iteration '{"event":"pause","reason":"user-requested"}'`.
5. Trigger the user's `/handoff` skill so the handoff lands in the project Handoffs dir, `~/.claude/handoffs/`, the Obsidian vault, and Notion (for opted-in projects).
6. Print a one-line confirmation: `paused at iteration <N>, milestone <id>, task <id>`.
7. Exit. The Stop hook will not re-prompt because status=paused.
