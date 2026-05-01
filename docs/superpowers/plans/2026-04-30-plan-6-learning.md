# FrinkLoop Plan 6 — Local Learning (Events, Profile, Consolidate)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Give FrinkLoop a lightweight local-learning layer. Every build emits structured events to a per-project `events.jsonl` log. After each iteration a `profile.json` is updated with aggregate stats (task counts, qa pass rate, blocker count, template used, recipes applied, duration). A `consolidate_profiles` helper sweeps all known project profiles and writes a global `~/.frinkloop/global-profile.json` summary so future projects can pick better templates and recipes.

**Architecture:** All state lives on disk (no network, no server). `plugin/lib/learning.sh` provides three entry points: `emit_event`, `update_profile`, `consolidate_profiles`. The mvp-loop SKILL.md already references "local learning" as a Plan 6 feature; this plan wires it in by documenting call sites and adding the helpers. The global profile is human-readable JSON — no ML, no embeddings. "Learning" = structured retrospective data.

**Tech Stack:** Bash + jq. No new runtime dependencies.

---

## File Structure

- Create: `plugin/lib/learning.sh`
- Create: `plugin/lib/schemas/event.schema.json`
- Create: `plugin/lib/schemas/profile.schema.json`
- Modify: `plugin/skills/mvp-loop/SKILL.md` — add learning call-site documentation
- Create: `tests/plan-6/test_learning.bats`
- Create: `tests/plan-6/test_learning_integration.bats`

---

## Task 1: Schemas

**Files:** `plugin/lib/schemas/event.schema.json`, `plugin/lib/schemas/profile.schema.json`

- [ ] **Step 1: Create event schema**

`plugin/lib/schemas/event.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop learning event",
  "type": "object",
  "required": ["schema_version", "event", "ts", "project"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "event": {
      "type": "string",
      "enum": ["task_done", "task_failed", "task_retried", "milestone_done", "qa_pass", "qa_fail", "blocker_opened", "project_done"]
    },
    "ts": { "type": "string" },
    "project": { "type": "string" },
    "task_id": { "type": "string" },
    "task_kind": {
      "type": "string",
      "enum": ["scaffold", "feature", "test", "fix", "doc", "deploy", "screenshot"]
    },
    "duration_s": { "type": "number", "minimum": 0 },
    "template": { "type": ["string", "null"] },
    "recipe": { "type": ["string", "null"] },
    "details": { "type": "object" }
  }
}
```

- [ ] **Step 2: Create profile schema**

`plugin/lib/schemas/profile.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop per-project profile",
  "type": "object",
  "required": ["schema_version", "project", "created_at", "updated_at", "task_stats"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "project": { "type": "string" },
    "created_at": { "type": "string" },
    "updated_at": { "type": "string" },
    "template_used": { "type": ["string", "null"] },
    "recipes_applied": { "type": "array", "items": { "type": "string" } },
    "task_stats": {
      "type": "object",
      "required": ["total", "done", "failed", "retried"],
      "additionalProperties": false,
      "properties": {
        "total":   { "type": "integer", "minimum": 0 },
        "done":    { "type": "integer", "minimum": 0 },
        "failed":  { "type": "integer", "minimum": 0 },
        "retried": { "type": "integer", "minimum": 0 }
      }
    },
    "qa_pass_rate":          { "type": "number", "minimum": 0, "maximum": 1 },
    "blockers":              { "type": "integer", "minimum": 0 },
    "milestones_completed":  { "type": "integer", "minimum": 0 },
    "total_duration_s":      { "type": "number",  "minimum": 0 }
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add plugin/lib/schemas/event.schema.json plugin/lib/schemas/profile.schema.json
git commit -m "feat(learning): add event and profile JSON schemas (Draft-07)"
```

---

## Task 2: `learning.sh` helpers

**Files:** `plugin/lib/learning.sh`, `tests/plan-6/test_learning.bats`

- [ ] **Step 1: Write failing tests**

`tests/plan-6/test_learning.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  export PROJECT_DIR="$TMPDIR/proj"
  mkdir -p "$FRINKLOOP_DIR" "$PROJECT_DIR"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  export PLUGIN_DIR
  source "$PLUGIN_DIR/lib/learning.sh"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "emit_event writes a JSONL line to events.jsonl" {
  emit_event task_done myproject T01 feature 5
  [ -f "$FRINKLOOP_DIR/events.jsonl" ]
  run jq -r '.event' "$FRINKLOOP_DIR/events.jsonl"
  [ "$output" = "task_done" ]
}

@test "emit_event appends multiple events" {
  emit_event task_done myproject T01 feature 3
  emit_event qa_pass   myproject T01 feature 1
  run wc -l < "$FRINKLOOP_DIR/events.jsonl"
  [ "$output" -eq 2 ]
}

@test "emit_event produces valid JSON on each line" {
  emit_event task_failed myproject T02 fix 10
  run jq -r '.event' "$FRINKLOOP_DIR/events.jsonl"
  [ "$status" -eq 0 ]
  [ "$output" = "task_failed" ]
}

@test "profile_init creates profile.json with zero stats" {
  profile_init myproject
  [ -f "$FRINKLOOP_DIR/profile.json" ]
  run jq -r '.project' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "myproject" ]
  run jq -r '.task_stats.total' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "0" ]
}

@test "profile_increment increments the given task_stats counter" {
  profile_init myproject
  profile_increment done
  profile_increment done
  profile_increment failed
  run jq -r '.task_stats.done' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
  run jq -r '.task_stats.failed' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "1" ]
}

@test "profile_set_template records template_used" {
  profile_init myproject
  profile_set_template vite-shadcn
  run jq -r '.template_used' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "vite-shadcn" ]
}

@test "profile_add_recipe appends to recipes_applied" {
  profile_init myproject
  profile_add_recipe tailwind
  profile_add_recipe playwright
  run jq -r '.recipes_applied | length' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
}

@test "profile_set_qa_rate stores qa_pass_rate" {
  profile_init myproject
  profile_set_qa_rate 0.85
  run jq -r '.qa_pass_rate' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "0.85" ]
}

@test "profile.json validates against schema" {
  profile_init myproject
  run npx --no-install ajv validate \
    -s "$PLUGIN_DIR/lib/schemas/profile.schema.json" \
    -d "$FRINKLOOP_DIR/profile.json" --strict=false
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run, expect FAIL**

Run: `bats tests/plan-6/test_learning.bats`
Expected: FAIL — `learning.sh` missing.

- [ ] **Step 3: Implement `learning.sh`**

`plugin/lib/learning.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop local-learning helpers.
# Caller must export FRINKLOOP_DIR before sourcing.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# emit_event <event_type> <project> <task_id> <task_kind> <duration_s> [template] [recipe]
emit_event() {
  local event="$1"
  local project="$2"
  local task_id="${3:-}"
  local task_kind="${4:-}"
  local duration_s="${5:-0}"
  local template="${6:-null}"
  local recipe="${7:-null}"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  jq -cn \
    --arg ev "$event" \
    --arg ts "$ts" \
    --arg proj "$project" \
    --arg tid "$task_id" \
    --arg kind "$task_kind" \
    --argjson dur "$duration_s" \
    --argjson tmpl "$([ "$template" = "null" ] && echo "null" || printf '"%s"' "$template")" \
    --argjson rec "$([ "$recipe" = "null" ] && echo "null" || printf '"%s"' "$recipe")" \
    '{schema_version:1, event:$ev, ts:$ts, project:$proj, task_id:$tid, task_kind:$kind, duration_s:$dur, template:$tmpl, recipe:$rec}' \
    >> "$FRINKLOOP_DIR/events.jsonl"
}

# profile_init <project>  — writes profile.json if it doesn't exist
profile_init() {
  local project="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  [ -f "$path" ] && return 0
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  jq -n \
    --arg proj "$project" \
    --arg ts "$ts" \
    '{schema_version:1, project:$proj, created_at:$ts, updated_at:$ts,
      template_used:null, recipes_applied:[],
      task_stats:{total:0, done:0, failed:0, retried:0},
      qa_pass_rate:0, blockers:0, milestones_completed:0, total_duration_s:0}' \
    > "$path"
}

# profile_increment <counter>  — increments task_stats.<counter> and task_stats.total
profile_increment() {
  local counter="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg c "$counter" --arg ts "$ts" \
    '.task_stats[$c] += 1 | .task_stats.total += 1 | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_set_template <name>
profile_set_template() {
  local tpl="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg t "$tpl" --arg ts "$ts" \
    '.template_used = $t | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_add_recipe <recipe_name>
profile_add_recipe() {
  local recipe="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg r "$recipe" --arg ts "$ts" \
    '.recipes_applied += [$r] | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_set_qa_rate <float 0-1>
profile_set_qa_rate() {
  local rate="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --argjson r "$rate" --arg ts "$ts" \
    '.qa_pass_rate = $r | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_increment_blockers
profile_increment_blockers() {
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg ts "$ts" \
    '.blockers += 1 | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_milestone_done
profile_milestone_done() {
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg ts "$ts" \
    '.milestones_completed += 1 | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# consolidate_profiles [global_dir]
# Sweeps all profile.json files found under global_dir (default: ~/.frinkloop/projects/)
# and writes a summary to global_dir/global-profile.json.
consolidate_profiles() {
  local global_dir="${1:-$HOME/.frinkloop/projects}"
  local output="$(dirname "$global_dir")/global-profile.json"
  local profiles=()
  while IFS= read -r -d '' f; do
    profiles+=("$f")
  done < <(find "$global_dir" -name "profile.json" -print0 2>/dev/null)

  if [ "${#profiles[@]}" -eq 0 ]; then
    jq -n '{schema_version:1, project_count:0, profiles:[]}' > "$output"
    return 0
  fi

  local merged="[]"
  for f in "${profiles[@]}"; do
    merged=$(echo "$merged" | jq --slurpfile p "$f" '. + $p')
  done

  echo "$merged" | jq \
    '{schema_version:1,
      project_count: length,
      profiles: .,
      top_templates: (map(select(.template_used != null) | .template_used) | group_by(.) | map({template:.[0], count:length}) | sort_by(-.count) | .[0:5]),
      top_recipes: (map(.recipes_applied // []) | flatten | group_by(.) | map({recipe:.[0], count:length}) | sort_by(-.count) | .[0:5]),
      avg_qa_pass_rate: (map(.qa_pass_rate) | if length > 0 then add/length else 0 end)
    }' > "$output"
}
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-6/test_learning.bats`
Expected: 9/9.

- [ ] **Step 5: Commit**

```bash
git add plugin/lib/learning.sh tests/plan-6/test_learning.bats
git commit -m "feat(learning): learning.sh — emit_event, profile_init/increment/set, consolidate_profiles"
```

---

## Task 3: Integration test + mvp-loop SKILL.md update

**Files:** `tests/plan-6/test_learning_integration.bats`, `plugin/skills/mvp-loop/SKILL.md`

- [ ] **Step 1: Write integration test**

`tests/plan-6/test_learning_integration.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  export PROJECT_DIR="$TMPDIR/proj"
  mkdir -p "$FRINKLOOP_DIR" "$PROJECT_DIR"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  export PLUGIN_DIR
  source "$PLUGIN_DIR/lib/learning.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "full profile lifecycle: init, set template, add recipe, increment, qa rate" {
  profile_init myproject
  profile_set_template vite-shadcn
  profile_add_recipe tailwind
  profile_add_recipe playwright
  profile_increment done
  profile_increment done
  profile_increment failed
  profile_set_qa_rate 0.67
  profile_milestone_done

  run jq -r '.template_used' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "vite-shadcn" ]
  run jq -r '.recipes_applied | length' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
  run jq -r '.task_stats.done' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "2" ]
  run jq -r '.milestones_completed' "$FRINKLOOP_DIR/profile.json"
  [ "$output" = "1" ]
}

@test "consolidate_profiles merges multiple project profiles" {
  local global_dir="$TMPDIR/projects"
  mkdir -p "$global_dir/proj-a" "$global_dir/proj-b"

  jq -n '{schema_version:1,project:"a",created_at:"2026-01-01T00:00:00Z",updated_at:"2026-01-01T00:00:00Z",template_used:"vite-shadcn",recipes_applied:["tailwind"],task_stats:{total:5,done:5,failed:0,retried:0},qa_pass_rate:1.0,blockers:0,milestones_completed:2,total_duration_s:120}' \
    > "$global_dir/proj-a/profile.json"

  jq -n '{schema_version:1,project:"b",created_at:"2026-01-02T00:00:00Z",updated_at:"2026-01-02T00:00:00Z",template_used:"vite-shadcn",recipes_applied:["playwright"],task_stats:{total:3,done:2,failed:1,retried:1},qa_pass_rate:0.5,blockers:1,milestones_completed:1,total_duration_s:60}' \
    > "$global_dir/proj-b/profile.json"

  consolidate_profiles "$global_dir"
  [ -f "$TMPDIR/global-profile.json" ]

  run jq -r '.project_count' "$TMPDIR/global-profile.json"
  [ "$output" = "2" ]
  run jq -r '.top_templates[0].template' "$TMPDIR/global-profile.json"
  [ "$output" = "vite-shadcn" ]
}

@test "mvp-loop SKILL.md references Plan 6 learning" {
  grep -q "learning" "$PLUGIN_DIR/skills/mvp-loop/SKILL.md"
}
```

- [ ] **Step 2: Run, expect FAIL (last test)**

The third test fails because SKILL.md doesn't reference learning yet.

- [ ] **Step 3: Update SKILL.md**

Append to the `mvp-loop` SKILL.md (after "What this skill is NOT"):

```markdown

## Local learning (Plan 6)

After each task outcome, emit a structured event:

```bash
source plugin/lib/learning.sh
emit_event task_done "$PROJECT_NAME" "$task_id" "$task_kind" "$duration_s"
# or on failure:
emit_event task_failed "$PROJECT_NAME" "$task_id" "$task_kind" "$duration_s"
```

After each `mark_task_done`, call `profile_increment done`. After a qa failure, call `profile_increment failed`. After a blocker, call `profile_increment_blockers`. After a milestone, call `profile_milestone_done`. At project end, call `consolidate_profiles` to update the global summary.
```

- [ ] **Step 4: Run, expect PASS**

Run: `bats tests/plan-6/test_learning_integration.bats` → 3/3.

- [ ] **Step 5: Run full suite**

`bats tests/plan-1/ tests/plan-2/ tests/plan-3/ tests/plan-4/ tests/plan-5/ tests/plan-6/`
Expected: 109 + 12 = 121 tests passing.

- [ ] **Step 6: Commit**

```bash
git add tests/plan-6/test_learning_integration.bats plugin/skills/mvp-loop/SKILL.md
git commit -m "feat(learning): integration test + wire learning into mvp-loop SKILL.md"
```

---

*End of Plan 6.*
