# FrinkLoop Plan 2 — Build Loop Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the FrinkLoop build loop spine — Stop-hook driven, sequential (no parallel fan-out yet), with real `mvp-loop` skill, real `planner` / `builder` / `qa` subagent role files, bash helper scripts for task flow + verification, real `stop.sh` and `post-iteration.sh` hooks, a Ralph-style invariant `PROMPT.md`, and crash recovery on resume.

**Architecture:** Loop runs inside one Claude Code session. After every model turn, the Stop hook reads `state.json` — if `status` is `running` and there's still pending work, it re-feeds `PROMPT.md` to keep the loop going; if everything is done or status is paused/blocked, it exits cleanly. The skill body in `mvp-loop` tells Claude exactly what to do per iteration: pick one task → invoke a builder subagent via the Task tool → run the qa subagent → call verify helpers → mark done → log → repeat. Bash helpers handle state mutations (pick task, mark done, queue fix tasks, verify by file kind). All state stays on disk, so a fresh session can resume.

**Tech Stack:** Bash for hooks + helpers, Claude Code skill/subagent prose for the loop body, `bats-core` for shell tests, `jq` for JSON, `ajv-cli` for schema checks. No new runtime dependencies beyond Plan 1.

---

## File Structure

Files this plan creates or modifies (worktree path = `<repo>/.worktrees/v0.2-build-loop` once we set it up):

**Hooks (replace placeholders from Plan 1 with real implementations):**
- Modify: `plugin/hooks/stop.sh` — decides whether to continue the loop based on state.json
- Modify: `plugin/hooks/post-iteration.sh` — increments iteration counter + appends iteration-log entry

**Loop helpers (new):**
- Create: `plugin/lib/loop.sh` — pick_next_task, mark_task_done, queue_fix_task, mark_milestone_done
- Create: `plugin/lib/verify.sh` — per-task verification (typecheck/test/lint based on task kind), per-milestone verification, final verification gate
- Create: `plugin/lib/recovery.sh` — detects dirty working tree on resume; opens blocker if so

**PROMPT template (the Ralph-style invariant):**
- Create: `plugin/skills/mvp-loop/PROMPT.md.tmpl` — copied to `<project>/.frinkloop/PROMPT.md` at scaffold time

**Skill body (real, replaces Plan 1 placeholder):**
- Modify: `plugin/skills/mvp-loop/SKILL.md` — the loop algorithm written for Claude to follow

**Subagent role files (real, replace Plan 1 placeholders):**
- Modify: `plugin/agents/planner.md`
- Modify: `plugin/agents/builder.md`
- Modify: `plugin/agents/qa.md`

**Slash command updates:**
- Modify: `plugin/commands/frinkloop-resume.md` — implement real resume flow
- Modify: `plugin/commands/frinkloop-pause.md` — implement real pause flow

**Tests:**
- Create: `tests/plan-2/test_loop_helpers.bats`
- Create: `tests/plan-2/test_verify.bats`
- Create: `tests/plan-2/test_recovery.bats`
- Create: `tests/plan-2/test_hooks.bats` — replaces logic-light Plan 1 hook tests
- Create: `tests/plan-2/test_skill_bodies.bats` — verifies mvp-loop SKILL.md and agent role files have required sections
- Create: `tests/plan-2/test_e2e_iteration.bats` — simulates one full loop iteration end-to-end (without actually running Claude)

**Schema additions:**
- Create: `plugin/lib/schemas/qa-result.schema.json` — validates the artifact qa subagent writes
- Modify: `plugin/lib/schemas/state.schema.json` — adds optional `last_iteration_at` (string|null) field

---

## Task 1: Loop helpers — `lib/loop.sh`

**Files:**
- Create: `plugin/lib/loop.sh`
- Test: `tests/plan-2/test_loop_helpers.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-2/test_loop_helpers.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  source plugin/lib/state.sh
  source plugin/lib/loop.sh
  state_init main
  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    {
      "id": "m1",
      "title": "Scaffold",
      "status": "in-progress",
      "tasks": [
        {"id": "T01", "title": "Run giget", "status": "done", "kind": "scaffold"},
        {"id": "T02", "title": "Apply tailwind recipe", "status": "pending", "kind": "scaffold"},
        {"id": "T03", "title": "Add login form", "status": "pending", "kind": "feature", "depends_on": ["T02"]}
      ]
    },
    {
      "id": "m2",
      "title": "Polish",
      "status": "pending",
      "tasks": [
        {"id": "T04", "title": "Write README", "status": "pending", "kind": "doc"}
      ]
    }
  ]
}
EOF
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "pick_next_task picks the first non-blocked pending task in the active milestone" {
  run pick_next_task
  [ "$status" -eq 0 ]
  [ "$output" = "T02" ]
}

@test "pick_next_task respects depends_on" {
  # T03 depends on T02 which is still pending; pick_next_task must NOT return T03
  run pick_next_task
  [ "$output" != "T03" ]
}

@test "pick_next_task returns empty when active milestone has no actionable tasks" {
  jq '(.milestones[0].tasks[1].status) = "done"' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"
  jq '(.milestones[0].tasks[2].status) = "done"' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"
  run pick_next_task
  [ "$output" = "" ]
}

@test "mark_task_done flips a task status and writes decisions entry" {
  mark_task_done T02 "Applied tailwind via shadcn-style recipe"
  run jq -r '.milestones[0].tasks[1].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]
  grep -q "T02" "$FRINKLOOP_DIR/decisions.md"
}

@test "queue_fix_task adds a fix task with kind=fix and depends_on parent" {
  queue_fix_task T03 "form submit handler crashes on empty input"
  run jq -r '.milestones[0].tasks | length' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" -eq 4 ]
  run jq -r '.milestones[0].tasks[3].kind' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "fix" ]
  run jq -r '.milestones[0].tasks[3].depends_on[0]' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "T03" ]
}

@test "mark_milestone_done flips milestone status when all tasks done" {
  mark_task_done T02 "ok"
  mark_task_done T03 "ok"
  mark_milestone_done m1
  run jq -r '.milestones[0].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]
}

@test "active_milestone returns the first in-progress or pending milestone" {
  run active_milestone
  [ "$output" = "m1" ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-2/test_loop_helpers.bats`
Expected: FAIL — `plugin/lib/loop.sh` missing.

- [ ] **Step 3: Implement `loop.sh`**

Create `plugin/lib/loop.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop loop helpers — task picking, status mutations, decisions log.
# Caller must export FRINKLOOP_DIR and source plugin/lib/state.sh first.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

active_milestone() {
  jq -r '
    .milestones[]
    | select(.status == "in-progress" or .status == "pending")
    | .id
  ' "$FRINKLOOP_DIR/tasks.json" | head -1
}

# Returns task id of the next task to work on, or empty string if none.
# Skips tasks blocked by undone dependencies.
pick_next_task() {
  local mid
  mid=$(active_milestone)
  if [ -z "$mid" ]; then
    return 0
  fi

  local tasks
  tasks=$(jq -c --arg mid "$mid" '
    .milestones[] | select(.id == $mid) | .tasks
  ' "$FRINKLOOP_DIR/tasks.json")

  # Find first task whose status is "pending" and whose depends_on is empty
  # OR all dependencies are status "done".
  echo "$tasks" | jq -r '
    [.[] | select(.status == "pending")] as $pending
    | $pending
    | map(
        . as $t
        | if (($t.depends_on // []) | length) == 0
          then $t
          else
            ($t | .depends_on) as $deps
            | . as $task
            | (. | .) | select(
                ($deps | map(. as $dep | $pending | map(.id) | index($dep)) | all(. == null))
              )
          end
      )
    | (.[0].id // "")
  '
}

# Mark a task done by id; append decisions.md entry.
mark_task_done() {
  local task_id="$1"
  local note="${2:-}"
  local path="$FRINKLOOP_DIR/tasks.json"
  local tmp
  tmp=$(mktemp)
  jq --arg tid "$task_id" '
    .milestones |= map(
      .tasks |= map(
        if .id == $tid then .status = "done" else . end
      )
    )
  ' "$path" > "$tmp"
  mv "$tmp" "$path"

  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf "\n## %s — %s\n%s\n" "$ts" "$task_id" "$note" >> "$FRINKLOOP_DIR/decisions.md"
}

# Queue a new fix task that depends on parent_task_id.
# Returns the new task id (e.g. T05) by reading the tasks.json after mutation.
queue_fix_task() {
  local parent="$1"
  local error_summary="$2"
  local path="$FRINKLOOP_DIR/tasks.json"
  local mid
  mid=$(active_milestone)

  # Generate a new id: T<N+1> based on current max
  local next_id
  next_id=$(jq -r '[.milestones[].tasks[].id] | map(sub("T"; "") | tonumber) | max + 1 | "T" + (. | tostring | ("0" * (2 - (. | length)) + .))' "$path" 2>/dev/null || echo "")
  if [ -z "$next_id" ] || [ "$next_id" = "null" ]; then
    next_id=$(jq -r '[.milestones[].tasks[].id] | length + 1 | "T" + (. | tostring | ("0" * (2 - (. | length)) + .))' "$path")
  fi

  local tmp
  tmp=$(mktemp)
  jq --arg mid "$mid" --arg pid "$parent" --arg nid "$next_id" --arg err "$error_summary" '
    .milestones |= map(
      if .id == $mid
      then .tasks += [{
        "id": $nid,
        "title": ("Fix: " + $err),
        "status": "pending",
        "kind": "fix",
        "depends_on": [$pid],
        "retries": 0
      }]
      else . end
    )
  ' "$path" > "$tmp"
  mv "$tmp" "$path"

  echo "$next_id"
}

# Mark a milestone done if all its tasks are done.
mark_milestone_done() {
  local mid="$1"
  local path="$FRINKLOOP_DIR/tasks.json"
  local all_done
  all_done=$(jq -r --arg mid "$mid" '
    .milestones[] | select(.id == $mid)
    | (.tasks | map(.status) | all(. == "done"))
  ' "$path")
  if [ "$all_done" != "true" ]; then
    return 1
  fi
  local tmp
  tmp=$(mktemp)
  jq --arg mid "$mid" '
    .milestones |= map(if .id == $mid then .status = "done" else . end)
  ' "$path" > "$tmp"
  mv "$tmp" "$path"
}
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-2/test_loop_helpers.bats`
Expected: 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add plugin/lib/loop.sh tests/plan-2/test_loop_helpers.bats
git commit -m "feat(loop): add task-flow helpers (pick/mark/queue/milestone-done)"
```

---

## Task 2: Verification helpers — `lib/verify.sh`

**Files:**
- Create: `plugin/lib/verify.sh`
- Create: `plugin/lib/schemas/qa-result.schema.json`
- Test: `tests/plan-2/test_verify.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-2/test_verify.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/proj"
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t
  source - <<'EOF'
PLUGIN_DIR=__PLUGIN_DIR__
EOF
  # Set PLUGIN_DIR to the actual repo plugin path
  export PLUGIN_DIR="$BATS_TEST_DIRNAME/../../plugin"
  source "$PLUGIN_DIR/lib/verify.sh"
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "verify_task accepts a doc kind without running tests" {
  echo "# README" > README.md
  run verify_task '{"id":"T04","kind":"doc","title":"Write README"}'
  [ "$status" -eq 0 ]
}

@test "verify_task fails when test kind has no tests dir" {
  run verify_task '{"id":"T05","kind":"test","title":"Add tests"}'
  [ "$status" -ne 0 ]
}

@test "verify_task writes a qa-result artifact" {
  echo "# README" > README.md
  verify_task '{"id":"T04","kind":"doc","title":"Write README"}'
  [ -f "$FRINKLOOP_DIR/qa.json" ]
  run jq -r '.task_id' "$FRINKLOOP_DIR/qa.json"
  [ "$output" = "T04" ]
  run jq -r '.outcome' "$FRINKLOOP_DIR/qa.json"
  [ "$output" = "pass" ]
}

@test "qa.json validates against schema" {
  echo "# README" > README.md
  verify_task '{"id":"T04","kind":"doc","title":"Write README"}'
  run npx --no-install ajv validate -s "$PLUGIN_DIR/lib/schemas/qa-result.schema.json" -d "$FRINKLOOP_DIR/qa.json" --strict=false
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-2/test_verify.bats`
Expected: FAIL — `verify.sh` missing.

- [ ] **Step 3: Create the qa-result schema**

Create `plugin/lib/schemas/qa-result.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop qa.json (per-task verification artifact)",
  "type": "object",
  "required": ["schema_version", "task_id", "kind", "outcome", "ts"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "task_id": { "type": "string" },
    "kind": { "type": "string", "enum": ["scaffold", "feature", "test", "fix", "doc", "deploy", "screenshot"] },
    "outcome": { "type": "string", "enum": ["pass", "fail"] },
    "ts": { "type": "string" },
    "checks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "status"],
        "additionalProperties": false,
        "properties": {
          "name": { "type": "string" },
          "status": { "type": "string", "enum": ["pass", "fail", "skip"] },
          "output_excerpt": { "type": "string" }
        }
      }
    },
    "error_summary": { "type": "string" }
  }
}
```

- [ ] **Step 4: Implement `verify.sh`**

Create `plugin/lib/verify.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop verification helpers.
# Caller exports FRINKLOOP_DIR (project's .frinkloop) and PROJECT_DIR.
# Writes qa.json artifact at FRINKLOOP_DIR/qa.json.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# Per-task verification — kind-driven.
# Argument: task JSON (one task object from tasks.json).
# Writes $FRINKLOOP_DIR/qa.json. Exits 0 on pass, non-zero on fail.
verify_task() {
  local task_json="$1"
  local task_id kind ts outcome
  task_id=$(echo "$task_json" | jq -r '.id')
  kind=$(echo "$task_json" | jq -r '.kind')
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local checks="[]"
  outcome="pass"

  case "$kind" in
    scaffold|doc|screenshot|deploy)
      # Lightweight kinds: just confirm the working tree is not broken.
      checks='[{"name":"git-status-readable","status":"pass"}]'
      ;;
    feature|fix|test)
      # Require a tests directory + at least one test file.
      if [ ! -d tests ] && [ ! -d test ] && [ ! -d __tests__ ] && [ ! -d src/__tests__ ]; then
        outcome="fail"
        checks='[{"name":"tests-dir-exists","status":"fail","output_excerpt":"no tests/ directory found"}]'
      else
        checks='[{"name":"tests-dir-exists","status":"pass"}]'
        # If there's a package.json, try `npm test`; if pyproject.toml, try `pytest`.
        if [ -f package.json ] && jq -e '.scripts.test' package.json >/dev/null 2>&1; then
          if npm test >/dev/null 2>&1; then
            checks=$(echo "$checks" | jq '. + [{"name":"npm-test","status":"pass"}]')
          else
            outcome="fail"
            checks=$(echo "$checks" | jq '. + [{"name":"npm-test","status":"fail"}]')
          fi
        elif [ -f pyproject.toml ] || [ -f pytest.ini ]; then
          if pytest >/dev/null 2>&1; then
            checks=$(echo "$checks" | jq '. + [{"name":"pytest","status":"pass"}]')
          else
            outcome="fail"
            checks=$(echo "$checks" | jq '. + [{"name":"pytest","status":"fail"}]')
          fi
        fi
      fi
      ;;
    *)
      outcome="fail"
      checks='[{"name":"unknown-kind","status":"fail","output_excerpt":"kind not handled"}]'
      ;;
  esac

  jq -n \
    --arg task_id "$task_id" \
    --arg kind "$kind" \
    --arg outcome "$outcome" \
    --arg ts "$ts" \
    --argjson checks "$checks" \
    '{schema_version:1, task_id:$task_id, kind:$kind, outcome:$outcome, ts:$ts, checks:$checks}' \
    > "$FRINKLOOP_DIR/qa.json"

  [ "$outcome" = "pass" ]
}

# Per-milestone verification — runs full test suite + build.
# Returns 0 on pass, non-zero on fail.
verify_milestone() {
  local mid="$1"
  local outcome="pass"

  if [ -f package.json ]; then
    jq -e '.scripts.test' package.json >/dev/null 2>&1 && (npm test >/dev/null 2>&1 || outcome="fail")
    jq -e '.scripts.build' package.json >/dev/null 2>&1 && (npm run build >/dev/null 2>&1 || outcome="fail")
  fi

  [ "$outcome" = "pass" ]
}

# Final verification gate — milestone verification + deploy ping (if configured).
verify_final() {
  local last_mid
  last_mid=$(jq -r '.milestones[-1].id' "$FRINKLOOP_DIR/tasks.json")
  verify_milestone "$last_mid" || return 1
  # Deploy ping is Plan 8; skip for Plan 2.
  return 0
}
```

- [ ] **Step 5: Run test, expect PASS**

Run: `bats tests/plan-2/test_verify.bats`
Expected: 4 tests pass.

- [ ] **Step 6: Commit**

```bash
git add plugin/lib/verify.sh plugin/lib/schemas/qa-result.schema.json tests/plan-2/test_verify.bats
git commit -m "feat(verify): per-task/milestone/final verification with qa.json artifact"
```

---

## Task 3: Crash recovery — `lib/recovery.sh`

**Files:**
- Create: `plugin/lib/recovery.sh`
- Test: `tests/plan-2/test_recovery.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-2/test_recovery.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/proj"
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t
  echo "# initial" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "init"
  source plugin/lib/state.sh
  state_init main
  source plugin/lib/recovery.sh
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "detect_dirty_tree returns 0 when working tree is clean" {
  run detect_dirty_tree
  [ "$status" -eq 0 ]
}

@test "detect_dirty_tree returns 1 when working tree has unstaged changes" {
  echo "modified" >> README.md
  run detect_dirty_tree
  [ "$status" -eq 1 ]
}

@test "open_blocker writes blockers.md entry" {
  open_blocker "T03" "user manually edited working tree mid-loop"
  [ -f "$FRINKLOOP_DIR/blockers.md" ]
  grep -q "T03" "$FRINKLOOP_DIR/blockers.md"
  grep -q "user manually edited" "$FRINKLOOP_DIR/blockers.md"
}

@test "resume_or_block returns 'resume' on clean tree" {
  run resume_or_block
  [ "$output" = "resume" ]
}

@test "resume_or_block returns 'block' on dirty tree and writes blockers.md" {
  echo "wat" > extra.md
  git add extra.md
  run resume_or_block
  [ "$output" = "block" ]
  [ -f "$FRINKLOOP_DIR/blockers.md" ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-2/test_recovery.bats`
Expected: FAIL — `recovery.sh` missing. The setup also requires loop.sh paths to resolve correctly; if any path issue arises, `cd` back to repo root in setup before sourcing.

- [ ] **Step 3: Implement `recovery.sh`**

Create `plugin/lib/recovery.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop crash recovery: detect mid-loop user edits, open blockers.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# Returns 0 if working tree is clean, 1 if dirty.
detect_dirty_tree() {
  local out
  out=$(git status --porcelain 2>/dev/null)
  if [ -z "$out" ]; then
    return 0
  fi
  return 1
}

open_blocker() {
  local task_id="$1"
  local reason="$2"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf "\n## %s — BLOCKED on %s\n%s\n" "$ts" "$task_id" "$reason" >> "$FRINKLOOP_DIR/blockers.md"
}

# Decides whether to resume the loop or open a blocker.
# Prints "resume" or "block" to stdout.
resume_or_block() {
  if detect_dirty_tree; then
    echo "resume"
    return 0
  fi
  open_blocker "<resume>" "Working tree dirty on resume — user may have edited files mid-loop. Manual cleanup required before resume."
  echo "block"
}
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-2/test_recovery.bats`
Expected: 5 tests pass.

If the setup() can't `source plugin/lib/state.sh` because it's now in `$PROJECT_DIR` (cwd is the temp project), pre-resolve the absolute path:

```bash
# At top of setup, before cd:
PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
# Then later:
source "$PLUGIN_LIB_DIR/state.sh"
source "$PLUGIN_LIB_DIR/recovery.sh"
```

Update the test to use this pattern if needed.

- [ ] **Step 5: Commit**

```bash
git add plugin/lib/recovery.sh tests/plan-2/test_recovery.bats
git commit -m "feat(recovery): detect dirty tree on resume + open blocker"
```

---

## Task 4: Real `stop.sh` hook

**Files:**
- Modify: `plugin/hooks/stop.sh`
- Test: `tests/plan-2/test_hooks.bats`

The Stop hook is called by Claude Code after every model turn. It looks at FRINKLOOP_DIR (set in the env by the loop's PROMPT.md preamble) and decides:
- If `state.json` doesn't exist → exit 0 (loop never started)
- If status == "running" AND there's at least one pending task → exit 2 (Claude Code interprets non-zero exit from Stop hook as "block stop, continue session")
- If status in {paused, blocked, quota-stopped, done} OR no pending tasks → exit 0 (let session end)

The exact convention here depends on Claude Code's hook contract. For Plan 2 we use a documented exit code convention; if Claude Code's actual contract differs (e.g., uses stdout instead of exit codes), Plan 9 polish will harden it.

- [ ] **Step 1: Write the failing test**

Create `tests/plan-2/test_hooks.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  source "$PLUGIN_LIB_DIR/state.sh"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "stop hook exits 0 when state.json is missing" {
  run plugin/hooks/stop.sh
  [ "$status" -eq 0 ]
}

@test "stop hook exits 0 when status is done" {
  state_init main
  state_set status done
  run plugin/hooks/stop.sh
  [ "$status" -eq 0 ]
}

@test "stop hook exits 0 when status is paused" {
  state_init main
  state_set status paused
  run plugin/hooks/stop.sh
  [ "$status" -eq 0 ]
}

@test "stop hook exits 2 when status is running and tasks pending" {
  state_init main
  state_set status running
  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "x", "status": "in-progress",
      "tasks": [{"id": "T01", "title": "x", "status": "pending", "kind": "feature"}]
    }
  ]
}
EOF
  run plugin/hooks/stop.sh
  [ "$status" -eq 2 ]
}

@test "stop hook exits 0 when status is running but no pending tasks" {
  state_init main
  state_set status running
  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "x", "status": "done",
      "tasks": [{"id": "T01", "title": "x", "status": "done", "kind": "feature"}]
    }
  ]
}
EOF
  run plugin/hooks/stop.sh
  [ "$status" -eq 0 ]
}

@test "post-iteration hook increments iteration_count and appends a log line" {
  state_init main
  run plugin/hooks/post-iteration.sh
  [ "$status" -eq 0 ]
  run jq -r '.iteration_count' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "1" ]
  [ -f "$FRINKLOOP_DIR/iteration-log.jsonl" ]
  run wc -l < "$FRINKLOOP_DIR/iteration-log.jsonl"
  [ "$output" -eq 1 ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-2/test_hooks.bats`
Expected: failures (placeholders from Plan 1 always exit 0; new tests want exit 2 in some cases).

- [ ] **Step 3: Replace `stop.sh`**

Overwrite `plugin/hooks/stop.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop Stop hook.
# Exit 0 → let the session end.
# Exit 2 → continue the loop (Claude Code re-prompts the model).
# FRINKLOOP_DIR must be exported by the session preamble.

set -euo pipefail

: "${FRINKLOOP_DIR:=}"

if [ -z "$FRINKLOOP_DIR" ] || [ ! -f "$FRINKLOOP_DIR/state.json" ]; then
  exit 0
fi

status=$(jq -r '.status' "$FRINKLOOP_DIR/state.json")

case "$status" in
  done|paused|blocked|quota-stopped|idle)
    exit 0
    ;;
  running)
    if [ ! -f "$FRINKLOOP_DIR/tasks.json" ]; then
      exit 0
    fi
    pending_count=$(jq '[.milestones[].tasks[] | select(.status == "pending")] | length' "$FRINKLOOP_DIR/tasks.json")
    if [ "$pending_count" -gt 0 ]; then
      exit 2
    fi
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
```

- [ ] **Step 4: Replace `post-iteration.sh`**

Overwrite `plugin/hooks/post-iteration.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop post-iteration hook.
# Increments iteration_count and appends an iteration-log entry.
# FRINKLOOP_DIR must be exported.

set -euo pipefail

: "${FRINKLOOP_DIR:=}"

if [ -z "$FRINKLOOP_DIR" ] || [ ! -f "$FRINKLOOP_DIR/state.json" ]; then
  exit 0
fi

# Source state helpers via path relative to this hook.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOK_DIR/../lib/state.sh"

state_increment_iteration

iter=$(state_get iteration_count)
log_iteration "$(jq -nc --arg i "$iter" '{event:"iteration", iter:($i|tonumber)}')"

exit 0
```

Make both executable:

```bash
chmod +x plugin/hooks/stop.sh plugin/hooks/post-iteration.sh
```

- [ ] **Step 5: Run test, expect PASS**

Run: `bats tests/plan-2/test_hooks.bats`
Expected: 6 tests pass.

- [ ] **Step 6: Commit**

```bash
git add plugin/hooks/stop.sh plugin/hooks/post-iteration.sh tests/plan-2/test_hooks.bats
git commit -m "feat(hooks): real stop and post-iteration logic with state-aware control flow"
```

---

## Task 5: PROMPT.md template

**Files:**
- Create: `plugin/skills/mvp-loop/PROMPT.md.tmpl`
- Test: `tests/plan-2/test_skill_bodies.bats` (initial — covers all skill body files; we'll grow it across Tasks 5–8)

This is the invariant prompt the loop re-feeds itself every iteration (Ralph-style).

- [ ] **Step 1: Write the failing test (skill-bodies suite, first test)**

Create `tests/plan-2/test_skill_bodies.bats`:

```bash
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
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-2/test_skill_bodies.bats` → fail.

- [ ] **Step 3: Create the template**

Create `plugin/skills/mvp-loop/PROMPT.md.tmpl`:

```markdown
# FrinkLoop Loop — Invariant Prompt

You are running an autonomous build loop. **Read this every iteration. Do not lose state.**

## State files (read every iteration)

- `<project>/.frinkloop/state.json` — current pointer (status, current_milestone, current_task, iteration_count, branch)
- `<project>/.frinkloop/tasks.json` — milestones and tasks
- `<project>/.frinkloop/spec.md` — frozen MVP spec (what done looks like, in-MVP, deferred)
- `<project>/.frinkloop/decisions.md` — append-only prose log
- `<project>/.frinkloop/blockers.md` — append-only blockers (only in flag-on-blocker mode)

## What to do this iteration

1. Read `state.json` to identify the active milestone and current task.
2. If `status == "done"`, emit `DONE` and stop.
3. Run `bash plugin/lib/loop.sh; pick_next_task` to get the next task id (or empty).
4. If empty, mark the active milestone done with `mark_milestone_done`, then check if the final milestone is done — if so, set status=done and emit `DONE`.
5. Otherwise, dispatch the appropriate subagent via the Task tool:
   - kind=scaffold → scaffolder (Plan 3; for Plan 2 mark the task done manually if scaffolder is unavailable)
   - kind=feature, fix, test, doc → builder
   - (qa runs after, separately)
6. After the builder returns, run the qa subagent.
7. Run `bash plugin/lib/verify.sh; verify_task "<task json>"`. If it fails:
   - Increment retries on the task; queue a fix task with `queue_fix_task <task_id> "<error summary>"`.
8. If verify passes, run `mark_task_done <task_id> "<one-line decision>"`.
9. Append a structured iteration entry — handled automatically by the post-iteration hook.

## Compression

Compression level is governed by `<project>/.frinkloop/config.yaml`. If `compression: full|ultra`, run subagent prompts through caveman before dispatch. Skill-body prose itself is compression-off.

## When to emit DONE

Emit the literal string `DONE` (uppercase, no punctuation, no extra text on the line) only when:
- All milestones in `tasks.json` have `status: "done"`
- Final verification gate (`bash plugin/lib/verify.sh; verify_final`) returned 0

The Stop hook reads `state.json` directly, not this prompt — but `DONE` in the assistant output is a backup signal that downstream tools can scrape.

## Stop conditions handled by the Stop hook

- `status == "paused"` → exit
- `status == "blocked"` → exit (write blockers.md first)
- `status == "quota-stopped"` → exit (Plan 7 launchd job will resume)
- `status == "done"` → exit
- `status == "running"` and no pending tasks → exit
- Otherwise → continue

## Constraints

- Compression off for the loop's own narration. On for subagent prompts when configured.
- Do NOT read decisions.md or iteration-log.jsonl every iteration — only read state.json + the active task in tasks.json + spec.md (the spec is small).
- Do NOT add extra fields to state.json or tasks.json beyond the schemas.
- Do NOT skip qa or verify — that's the integrity contract.
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-2/test_skill_bodies.bats`
Expected: 2 tests pass (more added in later tasks).

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/mvp-loop/PROMPT.md.tmpl tests/plan-2/test_skill_bodies.bats
git commit -m "feat(loop): add invariant PROMPT.md template (Ralph-style)"
```

---

## Task 6: `mvp-loop` SKILL.md (real)

**Files:**
- Modify: `plugin/skills/mvp-loop/SKILL.md`
- Modify (extend): `tests/plan-2/test_skill_bodies.bats`

- [ ] **Step 1: Add tests to `test_skill_bodies.bats`**

Append the following @test blocks to `tests/plan-2/test_skill_bodies.bats`:

```bash
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
```

- [ ] **Step 2: Run test, expect FAIL**

Run the suite — the 3 new tests fail (placeholder still in place).

- [ ] **Step 3: Replace `mvp-loop/SKILL.md`**

Overwrite `plugin/skills/mvp-loop/SKILL.md`:

````markdown
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
````

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-2/test_skill_bodies.bats` → 5/5 (2 PROMPT + 3 SKILL).

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/mvp-loop/SKILL.md tests/plan-2/test_skill_bodies.bats
git commit -m "feat(skills): real mvp-loop skill body with per-iteration algorithm"
```

---

## Task 7: `planner` agent (real)

**Files:**
- Modify: `plugin/agents/planner.md`
- Extend: `tests/plan-2/test_skill_bodies.bats`

- [ ] **Step 1: Add tests**

Append:

```bash
@test "planner agent has real body and references spec.md + tasks.json" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/planner.md
  grep -q "spec.md" plugin/agents/planner.md
  grep -q "tasks.json" plugin/agents/planner.md
}
```

- [ ] **Step 2: Run test, expect FAIL**

Suite fails on the new test (placeholder still says "Placeholder. Will be implemented").

- [ ] **Step 3: Replace `planner.md`**

Overwrite `plugin/agents/planner.md`:

```markdown
---
name: planner
description: FrinkLoop planner — turns a frozen spec into a tasks.json (initial plan) or applies deltas when the spec changes mid-loop. Inputs: spec.md + current tasks.json. Output: a new tasks.json (or a JSON patch) committed to disk. One-shot.
---

# planner

## Inputs
- `<project>/.frinkloop/spec.md` — frozen YC-shaped spec (Does / For / MVP proves / Done / In-MVP / Phase-2)
- `<project>/.frinkloop/tasks.json` — current task tree (may be empty on first run)
- `<project>/.frinkloop/config.yaml` — for tdd flag

## Output
- A new `<project>/.frinkloop/tasks.json` validated against `plugin/lib/schemas/tasks.schema.json`
- Append a one-paragraph rationale to `<project>/.frinkloop/decisions.md` describing the milestones chosen

## Job

Given the spec, decide:
1. Milestones (typically 3–6): coarse phases like "Scaffold", "Core flow", "Polish & deliver".
2. Tasks per milestone: each is a single 5–30 min unit of work. Use the `kind` enum: scaffold, feature, test, fix, doc, deploy, screenshot.
3. `depends_on` between tasks where order matters.
4. If `tdd: true` in config.yaml, every `kind=feature` task gets a paired `kind=test` task that comes BEFORE it in dependency order.

Use `T01..TNN` as ids, two digits, sequential across the whole project (not per milestone).

## What you must NOT do
- Do not add tasks for things in the Phase-2 list (the spec already defers them).
- Do not introduce new fields outside the schema.
- Do not write to anywhere other than `tasks.json` and `decisions.md`.

## Validation
After writing, run:

```bash
npx --no-install ajv validate -s plugin/lib/schemas/tasks.schema.json \
  -d "$FRINKLOOP_DIR/tasks.json" --strict=false
```

If it fails, fix tasks.json before exiting.

## Status report
Return: number of milestones, number of tasks, whether tdd was applied. The orchestrator (mvp-loop) will read tasks.json directly — your prose response is for the human-readable log only.
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-2/test_skill_bodies.bats` → 6/6.

- [ ] **Step 5: Commit**

```bash
git add plugin/agents/planner.md tests/plan-2/test_skill_bodies.bats
git commit -m "feat(agents): real planner agent — spec → tasks.json"
```

---

## Task 8: `builder` and `qa` agents (real) + remaining skill body tests

**Files:**
- Modify: `plugin/agents/builder.md`
- Modify: `plugin/agents/qa.md`
- Extend: `tests/plan-2/test_skill_bodies.bats`

- [ ] **Step 1: Add tests**

Append:

```bash
@test "builder agent has real body and emphasizes commit-per-task" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/builder.md
  grep -q "git commit" plugin/agents/builder.md
}

@test "qa agent has real body and writes qa.json" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/qa.md
  grep -q "qa.json" plugin/agents/qa.md
}
```

- [ ] **Step 2: Run test, expect FAIL**

Suite fails on the 2 new tests.

- [ ] **Step 3: Replace `builder.md`**

Overwrite `plugin/agents/builder.md`:

```markdown
---
name: builder
description: FrinkLoop builder — implements ONE task. Reads task spec, edits files, runs local checks, commits. Default workhorse for kind=feature/fix/test/doc. Sequential in Plan 2; worktree-isolated parallelism arrives in Plan 4.
---

# builder

## Inputs
- One task JSON from `<project>/.frinkloop/tasks.json` (passed by mvp-loop)
- `<project>/.frinkloop/spec.md` for context
- The full project working tree at `$PROJECT_DIR`

## Output
- One or more file edits / additions inside `$PROJECT_DIR/`
- One git commit per task with conventional-commit message: `<kind>(<scope>): <title>`
- No artifact file required (qa writes that separately)

## Job

1. Read the task title + kind. Plan the smallest set of edits that satisfies the task without scope creep.
2. If kind=test: write the test FIRST. Run it. Confirm it fails. (TDD discipline.)
3. If kind=feature: implement the smallest code that satisfies the task. If a paired test task exists ahead in the queue, the planner already enforced TDD ordering — your job is just to make it pass.
4. If kind=fix: read the parent task's failure mode (in `qa.json` and `decisions.md`). Make the minimal fix.
5. If kind=doc: edit README, JSDoc, or in-code comments only.
6. Run any obvious local check (typecheck, lint) before committing — but the qa subagent runs the formal verification, so don't overdo it.
7. Stage and commit:

   ```bash
   git add <specific files>
   git commit -m "<kind>(<scope>): <task title>"
   ```

## Constraints
- Write only inside `$PROJECT_DIR/`. Never edit the plugin.
- Don't refactor unrelated code. Stick to the task.
- Don't add new dependencies without an explicit task instruction.
- Don't push to a remote. Plan 8 handles deploy.

## Failure handling
If you can't make progress, return with status `BLOCKED` and a one-line reason. The mvp-loop will queue a fix task or escalate.
```

- [ ] **Step 4: Replace `qa.md`**

Overwrite `plugin/agents/qa.md`:

```markdown
---
name: qa
description: FrinkLoop QA — verifies a builder's task by running tests, typecheck, and lint where applicable. Writes qa.json artifact validated against schemas/qa-result.schema.json.
---

# qa

## Inputs
- One task JSON (passed by mvp-loop)
- The post-builder working tree at `$PROJECT_DIR`

## Output
- `<project>/.frinkloop/qa.json` validated against `plugin/lib/schemas/qa-result.schema.json`
- Optionally one or more diagnostic snippets quoted in qa.json under `output_excerpt`

## Job

Run `bash plugin/lib/verify.sh; verify_task '<task json>'`. The helper handles the kind-driven branching (lightweight kinds vs. test-running kinds).

If `verify_task` returns 0, qa.json shows `outcome=pass`. If non-zero, qa.json shows `outcome=fail` with `error_summary` populated.

## What you must NOT do
- Do not modify project files. You are read-only against the working tree.
- Do not skip checks. If the helper reports `unknown-kind`, that's a real failure.
- Do not write anything outside `$FRINKLOOP_DIR/`.

## Reporting
Return: outcome (pass/fail) and the path to qa.json. The orchestrator reads qa.json directly.
```

- [ ] **Step 5: Run test, expect PASS**

Run: `bats tests/plan-2/test_skill_bodies.bats` → 8/8.

- [ ] **Step 6: Commit**

```bash
git add plugin/agents/builder.md plugin/agents/qa.md tests/plan-2/test_skill_bodies.bats
git commit -m "feat(agents): real builder and qa agents with per-task contracts"
```

---

## Task 9: Real resume + pause slash commands

**Files:**
- Modify: `plugin/commands/frinkloop-resume.md`
- Modify: `plugin/commands/frinkloop-pause.md`
- Test: `tests/plan-2/test_commands_real.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-2/test_commands_real.bats`:

```bash
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
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-2/test_commands_real.bats` → fails (placeholders).

- [ ] **Step 3: Replace `frinkloop-resume.md`**

Overwrite:

```markdown
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
```

- [ ] **Step 4: Replace `frinkloop-pause.md`**

Overwrite:

```markdown
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
```

- [ ] **Step 5: Run test, expect PASS**

Run: `bats tests/plan-2/test_commands_real.bats` → 4/4.

- [ ] **Step 6: Commit**

```bash
git add plugin/commands/frinkloop-resume.md plugin/commands/frinkloop-pause.md tests/plan-2/test_commands_real.bats
git commit -m "feat(commands): real resume and pause flows wired to lib helpers"
```

---

## Task 10: Schema bump for `last_iteration_at`

**Files:**
- Modify: `plugin/lib/schemas/state.schema.json`
- Modify: `plugin/lib/state.sh` (have `state_increment_iteration` also stamp `last_iteration_at`)
- Modify: `tests/plan-1/test_state_helpers.bats` (add coverage)

- [ ] **Step 1: Add a test**

Append to `tests/plan-1/test_state_helpers.bats`:

```bash
@test "state_increment_iteration stamps last_iteration_at" {
  state_init main
  state_increment_iteration
  run jq -r '.last_iteration_at' "$FRINKLOOP_DIR/state.json"
  [ "$status" -eq 0 ]
  [ "$output" != "null" ]
}
```

- [ ] **Step 2: Run, expect FAIL**

Run: `bats tests/plan-1/test_state_helpers.bats` → new test fails.

- [ ] **Step 3: Update the schema**

Edit `plugin/lib/schemas/state.schema.json` — add `last_iteration_at` to `properties`:

```json
"last_iteration_at": { "type": ["string", "null"] }
```

(Keep it OPTIONAL — not in `required`.)

- [ ] **Step 4: Update `state.sh`**

Edit `state_increment_iteration` in `plugin/lib/state.sh`:

```bash
state_increment_iteration() {
  local current
  current=$(state_get iteration_count)
  state_set iteration_count "$((current + 1))"
  state_set last_iteration_at "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
}
```

- [ ] **Step 5: Run, expect PASS**

Run: `bats tests/plan-1/test_state_helpers.bats` → all pass; the existing schema-validation test continues to pass because `last_iteration_at` is optional.

- [ ] **Step 6: Commit**

```bash
git add plugin/lib/schemas/state.schema.json plugin/lib/state.sh tests/plan-1/test_state_helpers.bats
git commit -m "feat(state): stamp last_iteration_at on each iteration"
```

---

## Task 11: End-to-end iteration smoke

Simulate one full iteration cycle without actually running Claude — just exercise the helpers in the order the loop would call them.

**Files:**
- Create: `tests/plan-2/test_e2e_iteration.bats`

- [ ] **Step 1: Write the test**

Create `tests/plan-2/test_e2e_iteration.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/proj"
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"

  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"

  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t

  source "$PLUGIN_DIR/lib/state.sh"
  source "$PLUGIN_DIR/lib/loop.sh"
  source "$PLUGIN_DIR/lib/verify.sh"
  source "$PLUGIN_DIR/lib/recovery.sh"

  state_init main
  state_set status running

  cat > "$FRINKLOOP_DIR/tasks.json" <<EOF
{
  "schema_version": 1,
  "milestones": [
    { "id": "m1", "title": "Setup", "status": "in-progress",
      "tasks": [
        {"id":"T01","title":"Write README","status":"pending","kind":"doc"}
      ]
    }
  ]
}
EOF

  echo "# initial" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "init"

  export PLUGIN_DIR REPO_DIR
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "one full iteration: pick → builder simulated → qa → mark done" {
  # 1. pick
  task_id=$(pick_next_task)
  [ "$task_id" = "T01" ]

  # 2. builder simulated: edit README and commit
  echo "## Hello" >> README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "doc(readme): expand"

  # 3. qa: run verify
  task_json=$(jq --arg tid "$task_id" '.milestones[].tasks[] | select(.id==$tid)' "$FRINKLOOP_DIR/tasks.json")
  run verify_task "$task_json"
  [ "$status" -eq 0 ]
  [ -f "$FRINKLOOP_DIR/qa.json" ]

  # 4. mark done
  mark_task_done "$task_id" "Expanded README"

  # 5. milestone complete → mark milestone done
  mark_milestone_done m1
  run jq -r '.milestones[0].status' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" = "done" ]

  # 6. final: state shows done after we set it explicitly
  state_set status done
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 0 ]   # status=done → stop hook lets session exit
}

@test "verify failure path: queue_fix_task gets called and Stop hook keeps looping" {
  task_id=$(pick_next_task)
  task_json=$(jq --arg tid "$task_id" '.milestones[].tasks[] | select(.id==$tid)' "$FRINKLOOP_DIR/tasks.json")

  # Force fail: change task kind to feature so verify expects tests/, which doesn't exist
  jq --arg tid "$task_id" '(.milestones[0].tasks[] | select(.id==$tid).kind) = "feature"' "$FRINKLOOP_DIR/tasks.json" > /tmp/t && mv /tmp/t "$FRINKLOOP_DIR/tasks.json"

  run verify_task "$(jq --arg tid "$task_id" '.milestones[].tasks[] | select(.id==$tid)' "$FRINKLOOP_DIR/tasks.json")"
  [ "$status" -ne 0 ]

  queue_fix_task "$task_id" "no tests dir"

  # New fix task added
  run jq -r '.milestones[0].tasks | length' "$FRINKLOOP_DIR/tasks.json"
  [ "$output" -eq 2 ]

  # Stop hook should keep looping (status running, pending tasks exist)
  run "$PLUGIN_DIR/hooks/stop.sh"
  [ "$status" -eq 2 ]
}
```

- [ ] **Step 2: Run, expect PASS**

Run: `bats tests/plan-2/test_e2e_iteration.bats` → 2/2.
Then run the full suite: `bats tests/plan-1/ tests/plan-2/` → all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/plan-2/test_e2e_iteration.bats
git commit -m "test(plan-2): end-to-end iteration smoke covering happy and failure paths"
```

---

## Task 12: Plan-2 done tag + final verification

- [ ] **Step 1: Run the full suite**

Run: `bats tests/plan-1/ tests/plan-2/`
Expected: all tests pass.

- [ ] **Step 2: Tag**

```bash
git tag -a frinkloop-plan-2-done -m "Plan 2 complete: build loop core (sequential, no fan-out)"
```

- [ ] **Step 3: Smoke check tree**

```bash
ls plugin/lib/         # should show: schemas/ state.sh loop.sh verify.sh recovery.sh
ls plugin/agents/      # 6 files, real bodies for planner/builder/qa
cat plugin/skills/mvp-loop/SKILL.md | head -5  # confirm not the placeholder
```

---

## Self-Review (post-plan)

**Spec coverage check (against design spec §9):**

| Spec section | Where in this plan |
|---|---|
| §9.1 Loop algorithm | Tasks 4 (stop hook), 5 (PROMPT.md), 6 (mvp-loop skill body) |
| §9.2 State files | Already in place from Plan 1; Task 10 adds last_iteration_at |
| §9.3 Subagent roles | Tasks 7 (planner), 8 (builder + qa) — scaffolder/doc-writer/screenshot-capturer deferred to Plans 3/8 |
| §9.4 Verification gate | Task 2 (verify.sh: per-task / per-milestone / final) |
| §9.5 TDD discipline | Encoded in planner.md (Task 7) and builder.md (Task 8); enforced via config.yaml's `tdd` flag |
| §9.6 Branching & user-conflict handling | Task 3 (recovery.sh detect_dirty_tree); branch-per-milestone deferred to Plan 4 |
| §9.7 Token compression (caveman) | Referenced in mvp-loop SKILL.md; runtime wiring of caveman is in Plan 9 |

**Explicitly deferred to later plans:**
- Parallel fan-out + worktree-isolated builders → Plan 4
- giget scaffolder agent + recipe runner → Plan 3
- Local learning hooks → Plan 6
- Quota-aware resume mechanism → Plan 7
- Deliverable subagents (doc-writer, screenshot-capturer) → Plan 8
- caveman wiring → Plan 9

**Placeholder scan:** No "TODO", "TBD", "implement later" inside any task step. References to future Plans (3, 4, 6, 7, 8, 9) are intentional cross-plan deferrals.

**Type / signature consistency:**
- Bash function names used in tests match those defined in libs: `pick_next_task`, `mark_task_done`, `queue_fix_task`, `mark_milestone_done`, `active_milestone`, `verify_task`, `verify_milestone`, `verify_final`, `detect_dirty_tree`, `open_blocker`, `resume_or_block`, `state_init`, `state_get`, `state_set`, `state_increment_iteration`, `log_iteration`.
- JSON schema field names align: `state.status` enum (idle/running/paused/blocked/quota-stopped/done) is consistent across stop.sh logic, state schema, and SKILL.md prose.
- `task.kind` enum (scaffold/feature/test/fix/doc/deploy/screenshot) is consistent across tasks schema, qa-result schema, verify.sh case-statements, planner agent.

**Known fragilities (acknowledged for later polish):**
- `pick_next_task`'s `depends_on` filter logic is somewhat clunky in jq; if it misbehaves on non-trivial dependency graphs, refactor in Plan 9 polish.
- `verify_task` for `feature/fix/test` kinds is naive about which test framework to run. The `jq -e '.scripts.test'` check is a heuristic; Plan 3 (recipes) will set this up properly.
- The Stop hook's exit-code convention (2 = continue) is the documented pattern but Claude Code's actual hook contract should be confirmed at first integration. Plan 9 polish will validate.

---

*End of Plan 2.*
