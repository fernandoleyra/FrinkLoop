---
name: mvp-loop
description: FrinkLoop's autonomous build loop — Stop-hook spine. Reads disk state, picks one task, dispatches a builder subagent, runs qa, verifies, marks done, logs. Use after intake-chat finishes scaffolding. Sequential in Plan 2; parallel fan-out arrives in Plan 4.
---

# mvp-loop

This skill drives the FrinkLoop autonomous build loop. It runs inside one Claude Code session. The Stop hook keeps the session re-prompting until DONE.

## Preconditions

The intake-chat skill (or `/frinkloop new`) must have produced:
- `<project>/.frinkloop/spec.md`
- `<project>/.frinkloop/config.yaml`
- `<project>/.frinkloop/tasks.json`
- `<project>/.frinkloop/state.json` (status=running)
- `<project>/.frinkloop/PROMPT.md` (copied from the template)

`PROJECT_DIR` and `FRINKLOOP_DIR` must be exported in the session env. The session preamble sources `plugin/lib/state.sh`, `plugin/lib/loop.sh`, `plugin/lib/verify.sh`, and `plugin/lib/recovery.sh`.

## Per-iteration algorithm

Run these steps EVERY iteration. Read `<project>/.frinkloop/PROMPT.md` first thing every turn — that's the invariant.

1. Source helpers (idempotent).
2. Read `state.json`. If `status` ∈ {paused, blocked, quota-stopped, done}, exit (Stop hook will let the session end).
3. Call `pick_next_task`. If empty:
   - Look for an in-progress milestone. Run `mark_milestone_done <mid>`.
   - If the LAST milestone is now done, run `verify_final`. If it returns 0, set `status=done`, emit `DONE`, exit.
   - Otherwise the next milestone takes over; loop continues next iteration.
4. Read the picked task's full record from `tasks.json`.
5. Dispatch the right subagent via the Task tool:
   - `kind=scaffold` → `scaffolder` (Plan 3; if unavailable in Plan 2, mark done after a manual confirmation in decisions.md)
   - `kind=feature, fix, test, doc` → `builder`
   - `kind=deploy, screenshot` → defer to Plan 8 (mark deferred for now)
6. After builder finishes, dispatch the `qa` subagent. It writes `qa.json`.
7. Call `verify_task '<task json>'`. If non-zero:
   - Increment retries on the task in tasks.json.
   - If retries < 3: `queue_fix_task <task_id> "<one-line error summary>"`. Continue next iteration.
   - If retries == 3: open a blocker via `open_blocker <task_id> "verify failed 3x"`. Set `status=blocked`. Exit.
8. If verify passes: `mark_task_done <task_id> "<one-line rationale>"`.
9. The post-iteration hook handles iteration-log + state.iteration_count++.
10. End of turn. Stop hook decides whether to re-prompt.

## TDD discipline

Read `config.yaml` at start. If `tdd: true` (commercial mode default), every `kind=feature` task spawns a paired `kind=test` task that runs FIRST in the iteration order. The planner is responsible for inserting these test tasks.

## HITL handoff (milestone-checkpoint mode)

If `config.yaml` has `hitl: milestones`, after each milestone is marked done, set `status=paused` and emit a one-line summary. The Stop hook will exit. The user runs `/frinkloop resume <project>` to continue.

## Compression

Read `config.yaml`. If `compression ∈ {lite, full, ultra}`, prepend a caveman directive to subagent prompts when dispatching. Loop narration itself stays uncompressed.

## What this skill is NOT

- Not parallel — that's Plan 4
- Not template-aware — that's Plan 3
- Not deployment-aware — that's Plan 8
- Not learning-aware — that's Plan 6
- Not quota-aware — that's Plan 7

## On every dispatch

When invoking a subagent, the prompt MUST include:
- The exact task JSON (id, title, kind, depends_on, retries)
- Path constraints: subagent only writes to `$PROJECT_DIR/`, never to the plugin
- Output contract: subagent must write its artifact to a known path under `$FRINKLOOP_DIR/` (qa.json for qa; nothing extra for builder — it just edits files and commits)
- Compression directive (if config says so)
