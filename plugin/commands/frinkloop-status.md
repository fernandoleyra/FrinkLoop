---
description: Print a snapshot of FrinkLoop loop state for a project.
---

# /frinkloop status [<project>]

If `<project>` is given, read `<project>/.frinkloop/state.json` and `<project>/.frinkloop/iteration-log.jsonl` (last 5 lines). Print a compact summary: status, current milestone, current task, iteration count, last 5 log events.

If no project is given, list active loops from `~/.claude/plugins/frinkloop/state/active-loop.json` (Plan 7).

For Plan 1: only handles the explicit-project case. Reads via `plugin/lib/state.sh`.
