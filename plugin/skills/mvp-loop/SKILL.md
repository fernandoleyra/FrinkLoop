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

## Compression (Plan 9)

Read `config.yaml`. If `compression ∈ {lite, full, ultra}`, prepend a caveman directive to subagent prompts when dispatching. Loop narration itself stays uncompressed.

```bash
source plugin/lib/caveman.sh
compression=$(read_compression_level)
builder_prompt=$(caveman_prefix "$compression" "$raw_builder_prompt")
# Then dispatch the builder subagent with builder_prompt
```

The three levels:
- `lite` — terse prose, no filler
- `full` — caveman-style telegraphic
- `ultra` — 1-3 word answers, abbreviate everything

## Parallel fan-out (Plan 4)

When `pick_parallel_batch 10` returns ≥2 task ids, the loop dispatches multiple builder subagents simultaneously via the Task tool, capped at 10 per Claude Code limit.

### Steps

1. Source `plugin/lib/worktrees.sh`.
2. For each task id in the batch:
   - `create_task_worktree <id>` → returns the absolute worktree path
   - Set `status: in-progress` on the task in tasks.json
3. Dispatch all builders in a SINGLE assistant message with multiple Task tool calls. Each builder receives:
   - The task JSON
   - The absolute worktree path (its only writable directory)
   - The branch name (`frinkloop/task-<id>`)
   - Compression directive (if config says so)
4. After all builders complete (Claude Code awaits all parallel Task calls before continuing):
   - **Aggregator step:** for each completed task, read ONLY the artifact / commit sha. Do NOT read the subagent transcript.
   - Merge each `frinkloop/task-<id>` branch back into the project's main branch in id-sorted order, fast-forward where possible. Conflicts → mark the task BLOCKED.
   - Run qa for each. Run `verify_task` for each.
   - On verify pass: `mark_task_done <id>` and `remove_task_worktree <id>`.
   - On verify fail: `queue_fix_task <id> "<error>"`. Don't remove the worktree (next iteration may retry).

### When to fall back to sequential

- Batch size 1 → use the existing sequential path (skip worktree creation; build in main project tree as before)
- Any task without `paths_touched` set → that task runs alone (`pick_parallel_batch` already enforces this rule)

### Cleanup

After every milestone completes, run `prune_task_worktrees` to free disk.

## Local learning (Plan 6)

After each task outcome, emit a structured learning event and update the profile:

```bash
source plugin/lib/learning.sh
# on success:
emit_event task_done "$PROJECT_NAME" "$task_id" "$task_kind" "$duration_s"
profile_increment done
# on qa failure:
emit_event qa_fail "$PROJECT_NAME" "$task_id" "$task_kind" 0
profile_increment failed
# on blocker:
emit_event blocker_opened "$PROJECT_NAME" "$task_id" "$task_kind" 0
profile_increment_blockers
# after each milestone:
emit_event milestone_done "$PROJECT_NAME" "" "" 0
profile_milestone_done
# at project completion:
emit_event project_done "$PROJECT_NAME" "" "" 0
consolidate_profiles
```

Call `profile_init "$PROJECT_NAME"` once at loop start. Call `profile_set_template` and `profile_add_recipe` when the scaffolder applies them.

## What this skill is NOT

- Not parallel — that's Plan 4
- Not template-aware — that's Plan 3
- Not deployment-aware — that's Plan 8
- Not quota-aware — that's Plan 7

## On every dispatch

When invoking a subagent, the prompt MUST include:
- The exact task JSON (id, title, kind, depends_on, retries)
- Path constraints: subagent only writes to `$PROJECT_DIR/`, never to the plugin
- Output contract: subagent must write its artifact to a known path under `$FRINKLOOP_DIR/` (qa.json for qa; nothing extra for builder — it just edits files and commits)
- Compression directive (if config says so)
