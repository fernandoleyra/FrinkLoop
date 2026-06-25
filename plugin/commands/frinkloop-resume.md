---
description: Resume a paused or quota-stopped FrinkLoop loop for the named project.
---

# /frinkloop resume <project>

Resume the build loop for `<project>`.

## Steps

1. Resolve `<project>` to a directory (treat as path; if relative, resolve against `~/Developer/`).
2. Export `FRINKLOOP_DIR=<project>/.frinkloop` and `PROJECT_DIR=<project>`.
3. Validate `state.json` against `plugin/lib/schemas/state.schema.json`. If invalid, abort with a clear error.
4. Source `plugin/lib/state.sh`, `plugin/lib/loop.sh`, `plugin/lib/verify.sh`, `plugin/lib/recovery.sh`.
5. Run `resume_or_block` (from `recovery.sh`). It checks the working tree.
   - If output is `block` → tell the user the working tree was modified and a blocker was logged. Stop.
   - If output is `resume` → continue.
6. Set `status=running` via `state_set status running`.
7. Print a one-line status summary (status, current_milestone, current_task, iteration_count).
8. Hand off to the `mvp-loop` skill with PROMPT.md re-fed.

The Stop hook will then keep the loop ticking until DONE.
