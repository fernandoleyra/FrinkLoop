# FrinkLoop Plan 4 — Parallel Subagent Fan-out + Worktree Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the build loop with parallel fan-out — when N independent tasks are pending, the loop dispatches up to 10 builder subagents at once via the Task tool, each working in an isolated git worktree. An aggregator step reads only the per-builder artifacts (not transcripts) to update central state.

**Architecture:** New `lib/worktrees.sh` manages per-task worktree lifecycle (create, prune). `lib/loop.sh` gains `pick_parallel_batch` (returns up to N task ids whose deps are satisfied and which don't write to overlapping files — for v1 we use a coarse heuristic: assume tasks with disjoint `paths_touched` are safe to parallelize). `mvp-loop` SKILL.md adds a fan-out branch: if the batch returns ≥2 tasks, dispatch in parallel; else fall through to sequential. `builder` agent gains a worktree contract: it gets a worktree path, edits there, commits there. The orchestrator merges builder branches back to the project's main branch after all parallel builders finish.

**Tech Stack:** Bash + git worktrees, Claude Code's Task tool (10 parallel max), bats for tests, jq.

---

## File Structure

- Create: `plugin/lib/worktrees.sh` — create_task_worktree, prune_task_worktrees, list_task_worktrees
- Modify: `plugin/lib/loop.sh` — add `pick_parallel_batch(max=10)`
- Modify: `plugin/skills/mvp-loop/SKILL.md` — add §"Parallel fan-out"
- Modify: `plugin/agents/builder.md` — add §"Worktree contract"
- Add: schema field `paths_touched` (optional array of strings) to `tasks.schema.json`
- Create: `tests/plan-4/test_worktrees.bats`, `test_parallel_batch.bats`, `test_skill_updates.bats`

---

## Task 1: `lib/worktrees.sh`

**Files:** `plugin/lib/worktrees.sh`, `tests/plan-4/test_worktrees.bats`

- [ ] **Step 1: Tests**

`tests/plan-4/test_worktrees.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"

  export PROJECT_DIR="$TMPDIR/proj"
  mkdir -p "$PROJECT_DIR"
  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t
  echo "init" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "init"
  source "$PLUGIN_LIB_DIR/worktrees.sh"
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "create_task_worktree creates a worktree at the right path" {
  path=$(create_task_worktree T01)
  [ -d "$path" ]
  [ -f "$path/README.md" ]
}

@test "create_task_worktree creates a unique branch frinkloop/task-<id>" {
  create_task_worktree T01 >/dev/null
  run git branch --list 'frinkloop/task-T01'
  [ -n "$output" ]
}

@test "list_task_worktrees returns paths matching the task pattern" {
  create_task_worktree T01 >/dev/null
  create_task_worktree T02 >/dev/null
  run list_task_worktrees
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "frinkloop/task-T01"
  echo "$output" | grep -q "frinkloop/task-T02"
}

@test "remove_task_worktree cleans up cleanly" {
  path=$(create_task_worktree T01)
  remove_task_worktree T01
  [ ! -d "$path" ]
  run git branch --list 'frinkloop/task-T01'
  [ -z "$output" ]
}

@test "prune_task_worktrees removes all task worktrees" {
  create_task_worktree T01 >/dev/null
  create_task_worktree T02 >/dev/null
  prune_task_worktrees
  run list_task_worktrees
  [ -z "$output" ]
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement `lib/worktrees.sh`**

```bash
#!/usr/bin/env bash
# FrinkLoop worktree manager — per-task isolation for parallel builders.
# Caller's cwd must be a git repo (the project being built). Worktrees live under
# <project>/.frinkloop/worktrees/task-<id>/ branched from current HEAD.

set -euo pipefail

WORKTREE_BASE=".frinkloop/worktrees"

create_task_worktree() {
  local task_id="$1"
  local branch="frinkloop/task-${task_id}"
  local path="$WORKTREE_BASE/task-${task_id}"
  if git worktree list --porcelain | grep -q "$path$"; then
    echo "$(pwd)/$path"
    return 0
  fi
  git worktree add "$path" -b "$branch" >/dev/null
  echo "$(pwd)/$path"
}

remove_task_worktree() {
  local task_id="$1"
  local branch="frinkloop/task-${task_id}"
  local path="$WORKTREE_BASE/task-${task_id}"
  if [ -d "$path" ]; then
    git worktree remove --force "$path" >/dev/null 2>&1 || true
  fi
  git branch -D "$branch" >/dev/null 2>&1 || true
}

list_task_worktrees() {
  git worktree list --porcelain | awk '
    /^worktree / { wt=$2 }
    /^branch refs\/heads\/frinkloop\/task-/ { print wt }
  '
}

prune_task_worktrees() {
  local paths
  paths=$(list_task_worktrees)
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    local task_id="${p##*/task-}"
    remove_task_worktree "$task_id"
  done <<< "$paths"
}
```

- [ ] **Step 4: Run, expect PASS** (5/5)

- [ ] **Step 5: Commit**

```bash
git add plugin/lib/worktrees.sh tests/plan-4/test_worktrees.bats
git commit -m "feat(worktrees): per-task worktree manager for parallel builders"
```

---

## Task 2: `pick_parallel_batch` in `lib/loop.sh`

**Files:** Modify `plugin/lib/loop.sh`, modify `plugin/lib/schemas/tasks.schema.json`, create `tests/plan-4/test_parallel_batch.bats`

- [ ] **Step 1: Add `paths_touched` field to tasks schema**

In `plugin/lib/schemas/tasks.schema.json`, under task properties, add (optional):

```json
"paths_touched": { "type": "array", "items": { "type": "string" } }
```

(Keep additionalProperties: false; this just expands properties.)

- [ ] **Step 2: Tests**

`tests/plan-4/test_parallel_batch.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  source "$PLUGIN_LIB_DIR/state.sh"
  source "$PLUGIN_LIB_DIR/loop.sh"
  state_init main

  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "Build", "status": "in-progress",
      "tasks": [
        {"id":"T01","title":"Add login","status":"pending","kind":"feature","paths_touched":["src/auth/"]},
        {"id":"T02","title":"Add settings page","status":"pending","kind":"feature","paths_touched":["src/settings/"]},
        {"id":"T03","title":"Add billing page","status":"pending","kind":"feature","paths_touched":["src/billing/"]},
        {"id":"T04","title":"Refactor auth helper","status":"pending","kind":"feature","paths_touched":["src/auth/"]},
        {"id":"T05","title":"Update README","status":"pending","kind":"doc"}
      ]
    }
  ]
}
EOF
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "pick_parallel_batch returns up to N tasks with disjoint paths" {
  run pick_parallel_batch 10
  [ "$status" -eq 0 ]
  # Should return T01, T02, T03, T05 (T04 conflicts with T01 on src/auth/) — 4 ids
  echo "$output" | grep -q "T01"
  echo "$output" | grep -q "T02"
  echo "$output" | grep -q "T03"
  echo "$output" | grep -q "T05"
  ! echo "$output" | grep -q "T04"
}

@test "pick_parallel_batch respects the max parameter" {
  run pick_parallel_batch 2
  [ "$status" -eq 0 ]
  count=$(echo "$output" | wc -w)
  [ "$count" -eq 2 ]
}

@test "pick_parallel_batch returns empty when nothing is pending" {
  jq '.milestones[0].tasks |= map(.status = "done")' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"
  run pick_parallel_batch 10
  [ -z "$output" ]
}

@test "pick_parallel_batch always picks the first one (matches pick_next_task)" {
  run pick_parallel_batch 1
  [ "$output" = "T01" ]
}
```

- [ ] **Step 3: Run, expect FAIL**

- [ ] **Step 4: Add `pick_parallel_batch` to `lib/loop.sh`**

Append to `plugin/lib/loop.sh`:

```bash
# Returns up to MAX task ids that can run in parallel — pending, deps-satisfied, paths-disjoint.
# Tasks with no `paths_touched` are treated as conflicting with everything (safe default).
# Greedy: takes the first eligible, then keeps adding tasks whose paths don't overlap with already-taken set.
pick_parallel_batch() {
  local max="${1:-10}"
  local mid
  mid=$(active_milestone)
  if [ -z "$mid" ]; then
    return 0
  fi

  jq -r --arg mid "$mid" --argjson max "$max" '
    .milestones[] | select(.id == $mid) | .tasks as $all
    | $all | map(select(.status == "pending")) as $pending
    | $pending
    | reduce .[] as $t ([];
        # Skip tasks whose deps include any pending id
        if (
          ($t.depends_on // []) as $deps
          | $deps | map(. as $d | $pending | map(.id) | index($d)) | all(. == null)
        ) then
          # Already-claimed paths for the batch
          (. | map(.paths_touched // []) | add // []) as $claimed
          | ($t.paths_touched // []) as $tp
          | if (length < $max) and (
              ($tp | length) > 0 and ($claimed | map(. as $c | $tp | index($c)) | all(. == null))
              or
              # If the running batch is empty, always take this one (the first)
              (length == 0)
              or
              # Tasks without paths_touched only join the batch if it is empty (already handled above) — otherwise skip
              false
            ) then
              . + [$t]
            else
              .
            end
        else
          .
        end
      )
    | map(.id) | join(" ")
  ' "$FRINKLOOP_DIR/tasks.json"
}
```

- [ ] **Step 5: Run, expect PASS** (4/4)

- [ ] **Step 6: Commit**

```bash
git add plugin/lib/loop.sh plugin/lib/schemas/tasks.schema.json tests/plan-4/test_parallel_batch.bats
git commit -m "feat(loop): pick_parallel_batch with paths_touched conflict detection"
```

---

## Task 3: Update `mvp-loop` SKILL.md and `builder` agent for fan-out

**Files:** Modify `plugin/skills/mvp-loop/SKILL.md`, modify `plugin/agents/builder.md`, create `tests/plan-4/test_skill_updates.bats`

- [ ] **Step 1: Tests**

`tests/plan-4/test_skill_updates.bats`:

```bash
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
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Append to `mvp-loop/SKILL.md`**

Append a new section *before* the "What this skill is NOT" section:

```markdown
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
```

- [ ] **Step 4: Append to `agents/builder.md`**

Add a new section after "Failure handling":

```markdown
## Worktree contract (Plan 4)

When the loop dispatches you with a `WORKTREE_PATH` parameter, you operate inside that directory only:

- `cd "$WORKTREE_PATH"` is your first step
- All edits and commits happen in this worktree
- Your branch is `frinkloop/task-<id>` — you don't choose it, the orchestrator created it
- Don't merge anything yourself. The orchestrator does the fast-forward back to the project's main branch.
- Don't touch other worktrees or the main project tree (`$PROJECT_DIR` outside the worktree).

If `WORKTREE_PATH` is unset, you're in single-task mode — operate directly in `$PROJECT_DIR` as before (Plan 2 behavior).
```

- [ ] **Step 5: Run, expect PASS** (3/3)

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/mvp-loop/SKILL.md plugin/agents/builder.md tests/plan-4/test_skill_updates.bats
git commit -m "feat(loop): document parallel fan-out and worktree contract for builders"
```

---

## Task 4: Final verification + tag

- [ ] **Step 1: Run full suite**

```bash
bats tests/plan-1/ tests/plan-2/ tests/plan-3/ tests/plan-4/
```

Expected: 84 prior + 5 + 4 + 3 = 96 tests pass.

- [ ] **Step 2: Tag**

```bash
git tag -a frinkloop-plan-4-done -m "Plan 4 complete: parallel fan-out + worktree isolation"
```

- [ ] **Step 3: Push + PR**

```bash
git push -u origin frinkloop/v0.4-parallel
git push origin frinkloop-plan-4-done
gh pr create --base frinkloop/v0.3-templates --head frinkloop/v0.4-parallel \
  --title "Plan 4: Parallel fan-out + worktree isolation (stacks on Plan 3)" \
  --body "$(cat <<'EOF'
## Summary
Plan 4 of FrinkLoop. **Stacks on Plan 3 (PR #2)** — merge in order: PR #1 → PR #2 → this.

- `lib/worktrees.sh` — per-task worktree lifecycle (create / list / remove / prune)
- `lib/loop.sh#pick_parallel_batch` — up to 10 disjoint-path tasks at once
- Schema: `task.paths_touched` (optional array of strings)
- mvp-loop skill: parallel fan-out section
- builder agent: worktree contract

12 new tests, 96 total.

## Test plan
- [ ] CI: `bats tests/plan-1/ tests/plan-2/ tests/plan-3/ tests/plan-4/` → 96/96
- [ ] Visual: confirm fan-out documentation in mvp-loop SKILL.md is clear

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

- §9.6 branching (per-task worktree branches `frinkloop/task-<id>`): Tasks 1, 3 ✓
- Parallel orchestrator pattern from research: Tasks 2, 3 ✓
- Aggregator pattern (read artifacts, not transcripts): documented in skill (Task 3) ✓
- 10-parallel cap: documented in skill (Task 3) + enforced by Task tool itself ✓

**Function/name consistency:**
- `create_task_worktree`, `remove_task_worktree`, `list_task_worktrees`, `prune_task_worktrees`, `pick_parallel_batch` — defined in libs and referenced in skill prose

**Known limitations:**
- `paths_touched` heuristic is coarse — no real conflict detection beyond folder prefix match. Plan 9 polish may refine.
- The aggregator/fast-forward merge step is described in prose but no helper script — Plan 9 may add `lib/aggregator.sh` if needed.

---

*End of Plan 4.*
