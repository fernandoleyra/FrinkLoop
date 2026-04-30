# FrinkLoop Plan 1 — Plugin Foundation + Intake Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the FrinkLoop Claude Code plugin skeleton with installable manifest, six slash commands (stub-form), three skill directories, and a working intake-chat skill that produces a frozen `spec.md` + `config.yaml` from a 4-question YC-shaped conversation. No build loop yet — that's Plan 2.

**Architecture:** Plugin layout per design spec §6. Slash commands are thin Markdown entry points that invoke skills. Intake-chat is the only skill with real logic in this plan; the others are placeholder SKILL.md files referencing future plans. State helpers live in `lib/state.sh` so future plans (build loop) can reuse them. Tests are shell tests using `bats` for scripts + `ajv` for JSON schema validation.

**Tech Stack:** Claude Code plugin format (plugin.json, commands/, skills/, agents/, hooks/), Bash for scripts, YAML/JSON for config/state, Markdown for prose state, `bats-core` for shell tests, `ajv-cli` for JSON schema checks.

---

## File Structure

Files this plan creates (repo root = the FrinkLoop git repo at `/Users/leyra/Developer/03_AI_Agents/FrinkLoop`):

**Plugin skeleton:**
- Create: `plugin/plugin.json` — plugin manifest
- Create: `plugin/README.md` — plugin's own README (for marketplace)
- Create: `plugin/commands/frinkloop.md` — router command
- Create: `plugin/commands/frinkloop-new.md` — invokes intake-chat skill
- Create: `plugin/commands/frinkloop-resume.md` — stub
- Create: `plugin/commands/frinkloop-status.md` — stub
- Create: `plugin/commands/frinkloop-pause.md` — stub
- Create: `plugin/commands/frinkloop-ds.md` — stub
- Create: `plugin/commands/frinkloop-deliver.md` — stub

**Skills:**
- Create: `plugin/skills/intake-chat/SKILL.md` — the 9-step YC-shaped intake conversation
- Create: `plugin/skills/intake-chat/templates/spec.md.tmpl` — output spec template
- Create: `plugin/skills/intake-chat/templates/config.yaml.tmpl` — output config template
- Create: `plugin/skills/mvp-loop/SKILL.md` — placeholder, "implemented in Plan 2"
- Create: `plugin/skills/design-system-builder/SKILL.md` — placeholder, "implemented in Plan 5"

**Subagent role files:**
- Create: `plugin/agents/planner.md` — placeholder
- Create: `plugin/agents/scaffolder.md` — placeholder
- Create: `plugin/agents/builder.md` — placeholder
- Create: `plugin/agents/qa.md` — placeholder
- Create: `plugin/agents/doc-writer.md` — placeholder
- Create: `plugin/agents/screenshot-capturer.md` — placeholder

**Hooks (placeholders for Plan 2):**
- Create: `plugin/hooks/stop.sh` — placeholder, exits 0
- Create: `plugin/hooks/post-iteration.sh` — placeholder, exits 0

**Lib (state I/O helpers used by Plan 2):**
- Create: `plugin/lib/state.sh` — read/write helpers for state.json + iteration-log.jsonl
- Create: `plugin/lib/schemas/state.schema.json` — JSON schema for state.json
- Create: `plugin/lib/schemas/tasks.schema.json` — JSON schema for tasks.json
- Create: `plugin/lib/schemas/config.schema.json` — JSON schema for config.yaml (validated as JSON)

**Tests:**
- Create: `tests/plan-1/test_plugin_manifest.bats` — plugin.json validity
- Create: `tests/plan-1/test_state_helpers.bats` — lib/state.sh round-trip
- Create: `tests/plan-1/test_schemas.bats` — schema validity
- Create: `tests/plan-1/test_intake_outputs.bats` — intake-chat produces well-formed spec.md and config.yaml from a fixture answer set

**Repo housekeeping:**
- Modify: `README.md` — add a short pointer to `plugin/README.md` and to the design spec
- Create: `package.json` (dev deps only: `ajv-cli`, `bats-core`)
- Modify: `.gitignore` — add `node_modules/`, `.frinkloop/` (so projects scaffolded inside this repo don't pollute it)

---

## Task 1: Plugin manifest + dir tree

**Files:**
- Create: `plugin/plugin.json`
- Create: `plugin/README.md`
- Create: empty placeholder dirs via `.gitkeep`: `plugin/commands/`, `plugin/skills/`, `plugin/agents/`, `plugin/hooks/`, `plugin/lib/`, `plugin/lib/schemas/`, `plugin/templates/`, `plugin/recipes/`, `plugin/design-systems/`, `plugin/scripts/`
- Test: `tests/plan-1/test_plugin_manifest.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_plugin_manifest.bats`:

```bash
#!/usr/bin/env bats

@test "plugin.json exists and is valid JSON" {
  [ -f plugin/plugin.json ]
  run jq . plugin/plugin.json
  [ "$status" -eq 0 ]
}

@test "plugin.json has required fields" {
  run jq -r '.name' plugin/plugin.json
  [ "$output" = "frinkloop" ]

  run jq -r '.version' plugin/plugin.json
  [ "$status" -eq 0 ]
  [ -n "$output" ]

  run jq -r '.description' plugin/plugin.json
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "plugin dir layout exists" {
  for d in commands skills agents hooks lib lib/schemas templates recipes design-systems scripts; do
    [ -d "plugin/$d" ] || (echo "missing plugin/$d" && false)
  done
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_plugin_manifest.bats`
Expected: FAIL — `plugin/plugin.json` not found.

- [ ] **Step 3: Create the plugin manifest**

Create `plugin/plugin.json`:

```json
{
  "name": "frinkloop",
  "version": "0.1.0",
  "description": "Autonomous MVP development for Claude Code: intake → scaffold → build → verify → deliver. Token-friendly, parallel, learns locally.",
  "author": "Fernando Leyra",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/fernandoleyra/FrinkLoop"
  },
  "keywords": ["autonomous", "mvp", "scaffolder", "claude-code", "agent"],
  "claudeCode": {
    "minVersion": "0.10.0"
  }
}
```

- [ ] **Step 4: Create the dir tree**

Run:

```bash
mkdir -p plugin/{commands,skills,agents,hooks,lib/schemas,templates,recipes,design-systems,scripts}
for d in commands skills agents hooks lib lib/schemas templates recipes design-systems scripts; do
  touch "plugin/$d/.gitkeep"
done
```

- [ ] **Step 5: Create plugin/README.md**

Create `plugin/README.md`:

```markdown
# FrinkLoop

> Autonomous MVP development for Claude Code. Intake → scaffold → build → verify → deliver.

## What it does

FrinkLoop turns a 4-question intake conversation into a deploy-ready MVP with a README, a landing page, screenshots, and a Phase-2 plan — fully autonomously, surviving Claude Code 5-hour usage windows.

## Install

```bash
claude plugin marketplace add fernandoleyra/FrinkLoop
claude plugin install frinkloop@frinkloop
```

## Quick start

```
/frinkloop new
```

## Commands

| Command | Purpose |
|---------|---------|
| `/frinkloop` | Router/help |
| `/frinkloop new` | Start intake chat → scaffold → build |
| `/frinkloop resume <project>` | Resume a paused or quota-stopped loop |
| `/frinkloop status [<project>]` | Snapshot of loop state |
| `/frinkloop pause <project>` | Flush state, write handoff, exit cleanly |
| `/frinkloop ds` | Design system manager |
| `/frinkloop deliver <project>` | Run the deliverable packaging step |

## Status

Early development. See `docs/superpowers/specs/2026-04-30-frinkloop-plugin-redesign-design.md` for the design and `docs/superpowers/plans/2026-04-30-frinkloop-roadmap.md` for implementation status.

## Privacy

Local-only. No telemetry. No analytics. Network calls limited to: template fetches via `giget`, deploys you opt into, and `gh` push for design systems if you opt in.

## Acknowledgements

- [Ralph Loop](https://ghuntley.com/ralph) by Geoffrey Huntley — the disk-state Stop-hook loop primitive
- [caveman](https://github.com/JuliusBrussee/caveman) by Julius Brussee — token compression
- [superpowers](https://github.com/jesseduffield/superpowers) — TDD, verification, brainstorming, subagent patterns
- Y Combinator — pitch frameworks for intake structure and communication

## License

MIT
```

- [ ] **Step 6: Run test, expect PASS**

Run: `bats tests/plan-1/test_plugin_manifest.bats`
Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```bash
git add plugin/plugin.json plugin/README.md plugin/**/.gitkeep tests/plan-1/test_plugin_manifest.bats
git commit -m "feat(plugin): scaffold FrinkLoop plugin manifest and dir tree"
```

---

## Task 2: Test harness setup (`package.json`, `bats`, `ajv-cli`)

**Files:**
- Create: `package.json`
- Modify: `.gitignore`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_dev_deps.bats`:

```bash
#!/usr/bin/env bats

@test "package.json exists and lists test deps" {
  [ -f package.json ]
  run jq -r '.devDependencies."ajv-cli"' package.json
  [ "$status" -eq 0 ]
  [ "$output" != "null" ]
}

@test "ajv-cli is callable" {
  run npx --no-install ajv --version
  [ "$status" -eq 0 ]
}

@test "bats is callable" {
  run bats --version
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_dev_deps.bats`
Expected: FAIL — `package.json` missing or `ajv` not installed.

- [ ] **Step 3: Create `package.json`**

Create `package.json`:

```json
{
  "name": "frinkloop-dev",
  "version": "0.1.0",
  "private": true,
  "description": "Dev dependencies for FrinkLoop plugin development and tests",
  "scripts": {
    "test": "bats tests/"
  },
  "devDependencies": {
    "ajv-cli": "^5.0.0",
    "ajv-formats": "^3.0.1"
  }
}
```

- [ ] **Step 4: Install deps + ensure bats available**

```bash
npm install
# bats is system-installed: brew install bats-core (macOS) or apt install bats (Linux)
command -v bats || brew install bats-core
```

- [ ] **Step 5: Update `.gitignore`**

Append to `.gitignore`:

```
node_modules/
.frinkloop/
```

- [ ] **Step 6: Run test, expect PASS**

Run: `bats tests/plan-1/test_dev_deps.bats`
Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```bash
git add package.json package-lock.json .gitignore tests/plan-1/test_dev_deps.bats
git commit -m "chore: add ajv-cli + bats test harness"
```

---

## Task 3: JSON schemas for state, tasks, config

**Files:**
- Create: `plugin/lib/schemas/state.schema.json`
- Create: `plugin/lib/schemas/tasks.schema.json`
- Create: `plugin/lib/schemas/config.schema.json`
- Test: `tests/plan-1/test_schemas.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_schemas.bats`:

```bash
#!/usr/bin/env bats

@test "state schema validates a minimal valid example" {
  cat > /tmp/state-valid.json <<EOF
{
  "schema_version": 1,
  "current_milestone": null,
  "current_task": null,
  "iteration_count": 0,
  "branch": "main",
  "last_verified_sha": null,
  "status": "idle"
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d /tmp/state-valid.json --strict=false
  [ "$status" -eq 0 ]
}

@test "state schema rejects missing schema_version" {
  cat > /tmp/state-bad.json <<EOF
{ "iteration_count": 0 }
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d /tmp/state-bad.json --strict=false
  [ "$status" -ne 0 ]
}

@test "tasks schema validates a milestones+tasks structure" {
  cat > /tmp/tasks-valid.json <<EOF
{
  "schema_version": 1,
  "milestones": [{
    "id": "m1",
    "title": "Scaffold",
    "status": "pending",
    "tasks": [{
      "id": "T01",
      "title": "Run giget",
      "status": "pending",
      "kind": "scaffold"
    }]
  }]
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/tasks.schema.json -d /tmp/tasks-valid.json --strict=false
  [ "$status" -eq 0 ]
}

@test "config schema validates a minimal config" {
  cat > /tmp/config-valid.json <<EOF
{
  "schema_version": 1,
  "project": "demo",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "compression": "full",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel"
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/config-valid.json --strict=false
  [ "$status" -eq 0 ]
}

@test "config schema rejects invalid mode" {
  cat > /tmp/config-bad.json <<EOF
{
  "schema_version": 1,
  "project": "demo",
  "mode": "yolo",
  "hitl": "fully-autonomous",
  "compression": "full",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel"
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/config-bad.json --strict=false
  [ "$status" -ne 0 ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_schemas.bats`
Expected: FAIL — schema files missing.

- [ ] **Step 3: Create state schema**

Create `plugin/lib/schemas/state.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop state.json",
  "type": "object",
  "required": ["schema_version", "iteration_count", "branch", "status"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "current_milestone": { "type": ["string", "null"] },
    "current_task": { "type": ["string", "null"] },
    "iteration_count": { "type": "integer", "minimum": 0 },
    "branch": { "type": "string" },
    "last_verified_sha": { "type": ["string", "null"] },
    "status": {
      "type": "string",
      "enum": ["idle", "running", "paused", "blocked", "quota-stopped", "done"]
    }
  }
}
```

- [ ] **Step 4: Create tasks schema**

Create `plugin/lib/schemas/tasks.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop tasks.json",
  "type": "object",
  "required": ["schema_version", "milestones"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "milestones": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "status", "tasks"],
        "additionalProperties": false,
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "status": { "type": "string", "enum": ["pending", "in-progress", "done", "blocked"] },
          "branch": { "type": "string" },
          "tasks": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["id", "title", "status", "kind"],
              "additionalProperties": false,
              "properties": {
                "id": { "type": "string" },
                "title": { "type": "string" },
                "status": { "type": "string", "enum": ["pending", "in-progress", "done", "blocked", "deferred"] },
                "kind": { "type": "string", "enum": ["scaffold", "feature", "test", "fix", "doc", "deploy", "screenshot"] },
                "depends_on": { "type": "array", "items": { "type": "string" } },
                "defer_to_phase_2": { "type": "boolean" },
                "retries": { "type": "integer", "minimum": 0 },
                "notes": { "type": "string" }
              }
            }
          }
        }
      }
    }
  }
}
```

- [ ] **Step 5: Create config schema**

Create `plugin/lib/schemas/config.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop config.yaml (validated as JSON)",
  "type": "object",
  "required": [
    "schema_version", "project", "mode", "hitl", "compression",
    "platform", "template", "design_system", "deploy_target"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "project": { "type": "string", "minLength": 1 },
    "mode": { "type": "string", "enum": ["hackathon", "commercial", "internal-demo"] },
    "hitl": { "type": "string", "enum": ["fully-autonomous", "milestones", "flag-on-blocker"] },
    "compression": { "type": "string", "enum": ["off", "lite", "full", "ultra"] },
    "platform": {
      "type": "string",
      "enum": [
        "web-fullstack", "spa-static", "marketing-landing",
        "node-api", "python-api", "node-cli", "python-cli",
        "mobile-expo", "browser-extension", "discord-bot", "slack-bot"
      ]
    },
    "template": { "type": "string", "minLength": 1 },
    "design_system": { "type": "string", "minLength": 1 },
    "deploy_target": {
      "type": "string",
      "enum": ["vercel", "netlify", "cloudflare-pages", "render", "fly", "manual-package", "expo-dev"]
    },
    "tdd": { "type": "boolean" },
    "exclusions": { "type": "array", "items": { "type": "string" } }
  }
}
```

- [ ] **Step 6: Run test, expect PASS**

Run: `bats tests/plan-1/test_schemas.bats`
Expected: 5 tests pass.

- [ ] **Step 7: Commit**

```bash
git add plugin/lib/schemas/ tests/plan-1/test_schemas.bats
git commit -m "feat(schemas): add JSON schemas for state, tasks, and config"
```

---

## Task 4: State helpers (`lib/state.sh`)

**Files:**
- Create: `plugin/lib/state.sh`
- Test: `tests/plan-1/test_state_helpers.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_state_helpers.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
  source plugin/lib/state.sh
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "state_init creates a valid state.json" {
  state_init main
  [ -f "$FRINKLOOP_DIR/state.json" ]
  run jq -r '.status' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "idle" ]
  run jq -r '.iteration_count' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "0" ]
  run jq -r '.branch' "$FRINKLOOP_DIR/state.json"
  [ "$output" = "main" ]
}

@test "state_get returns a field value" {
  state_init main
  run state_get status
  [ "$status" -eq 0 ]
  [ "$output" = "idle" ]
}

@test "state_set updates a field and round-trips" {
  state_init main
  state_set status running
  run state_get status
  [ "$output" = "running" ]
}

@test "log_iteration appends a JSONL line" {
  state_init main
  log_iteration '{"event":"task_done","task_id":"T01"}'
  log_iteration '{"event":"task_done","task_id":"T02"}'
  run wc -l < "$FRINKLOOP_DIR/iteration-log.jsonl"
  [ "$output" -eq 2 ]
}

@test "state_validate against schema passes for fresh state" {
  state_init main
  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d "$FRINKLOOP_DIR/state.json" --strict=false
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_state_helpers.bats`
Expected: FAIL — `plugin/lib/state.sh` missing.

- [ ] **Step 3: Implement `state.sh`**

Create `plugin/lib/state.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop state I/O helpers.
# Reads/writes state.json and iteration-log.jsonl in $FRINKLOOP_DIR.
# Caller must export FRINKLOOP_DIR before sourcing.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set (e.g. <project>/.frinkloop)}"

state_init() {
  local branch="${1:-main}"
  local path="$FRINKLOOP_DIR/state.json"
  if [ -f "$path" ]; then
    return 0
  fi
  cat > "$path" <<EOF
{
  "schema_version": 1,
  "current_milestone": null,
  "current_task": null,
  "iteration_count": 0,
  "branch": "$branch",
  "last_verified_sha": null,
  "status": "idle"
}
EOF
}

state_get() {
  local field="$1"
  jq -r ".${field}" "$FRINKLOOP_DIR/state.json"
}

state_set() {
  local field="$1"
  local value="$2"
  local path="$FRINKLOOP_DIR/state.json"
  local tmp
  tmp=$(mktemp)
  if [[ "$value" =~ ^-?[0-9]+$ ]] || [[ "$value" == "true" ]] || [[ "$value" == "false" ]] || [[ "$value" == "null" ]]; then
    jq ".${field} = ${value}" "$path" > "$tmp"
  else
    jq --arg v "$value" ".${field} = \$v" "$path" > "$tmp"
  fi
  mv "$tmp" "$path"
}

state_increment_iteration() {
  local current
  current=$(state_get iteration_count)
  state_set iteration_count "$((current + 1))"
}

log_iteration() {
  local payload="$1"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "$payload" | jq --arg ts "$ts" '. + {ts: $ts}' >> "$FRINKLOOP_DIR/iteration-log.jsonl"
}
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-1/test_state_helpers.bats`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add plugin/lib/state.sh tests/plan-1/test_state_helpers.bats
git commit -m "feat(lib): add state I/O helpers with schema-validated round-trip"
```

---

## Task 5: Slash command stubs (router + 6 commands)

**Files:**
- Create: `plugin/commands/frinkloop.md`
- Create: `plugin/commands/frinkloop-new.md`
- Create: `plugin/commands/frinkloop-resume.md`
- Create: `plugin/commands/frinkloop-status.md`
- Create: `plugin/commands/frinkloop-pause.md`
- Create: `plugin/commands/frinkloop-ds.md`
- Create: `plugin/commands/frinkloop-deliver.md`
- Test: `tests/plan-1/test_commands.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_commands.bats`:

```bash
#!/usr/bin/env bats

@test "all 7 command files exist" {
  for c in frinkloop frinkloop-new frinkloop-resume frinkloop-status frinkloop-pause frinkloop-ds frinkloop-deliver; do
    [ -f "plugin/commands/$c.md" ] || (echo "missing $c.md" && false)
  done
}

@test "each command file has YAML frontmatter with description" {
  for c in plugin/commands/*.md; do
    head -1 "$c" | grep -q '^---$' || (echo "no frontmatter in $c" && false)
    grep -q '^description:' "$c" || (echo "no description in $c" && false)
  done
}

@test "frinkloop-new references the intake-chat skill" {
  grep -q "intake-chat" plugin/commands/frinkloop-new.md
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_commands.bats`
Expected: FAIL — command files missing.

- [ ] **Step 3: Create the router command**

Create `plugin/commands/frinkloop.md`:

```markdown
---
description: FrinkLoop — autonomous MVP development. Show help and active projects.
---

# /frinkloop

Print this help text:

```
FrinkLoop — autonomous MVP development

  /frinkloop new                Start a new MVP (intake → scaffold → build → deliver)
  /frinkloop resume <project>   Resume a paused or quota-stopped loop
  /frinkloop status [<project>] Snapshot of loop state
  /frinkloop pause <project>    Flush state, write handoff, exit cleanly
  /frinkloop ds                 Design system manager
  /frinkloop deliver <project>  Run the deliverable packaging step

Privacy: local-only, no telemetry. See ~/.claude/plugins/.../frinkloop/README.md.
```

Then list any active loops by reading `~/.claude/plugins/frinkloop/state/active-loop.json` if present.
```

- [ ] **Step 4: Create the `new` command**

Create `plugin/commands/frinkloop-new.md`:

```markdown
---
description: Start a new FrinkLoop MVP — runs the intake-chat skill, then scaffolds and hands off to the build loop.
---

# /frinkloop new

Invoke the `intake-chat` skill to walk the user through the 4-question YC-shaped clarifier and downstream steps. The skill produces `<project>/.frinkloop/spec.md` and `<project>/.frinkloop/config.yaml`.

After the intake skill finishes:
1. Confirm scaffold path with the user (default: `~/Developer/<project-slug>`).
2. Hand off to the `mvp-loop` skill (Plan 2). For now (Plan 1), stop after intake and tell the user: "Spec written. Build loop arrives in Plan 2."
```

- [ ] **Step 5: Create the 5 stub commands**

Create `plugin/commands/frinkloop-resume.md`:

```markdown
---
description: Resume a paused or quota-stopped FrinkLoop loop for the named project.
---

# /frinkloop resume <project>

(Plan 2.) Will load `<project>/.frinkloop/state.json`, validate, and resume the `mvp-loop` skill.

For now: print "Resume arrives in Plan 2."
```

Create `plugin/commands/frinkloop-status.md`:

```markdown
---
description: Print a snapshot of FrinkLoop loop state for a project.
---

# /frinkloop status [<project>]

If `<project>` is given, read `<project>/.frinkloop/state.json` and `<project>/.frinkloop/iteration-log.jsonl` (last 5 lines). Print a compact summary: status, current milestone, current task, iteration count, last 5 log events.

If no project is given, list active loops from `~/.claude/plugins/frinkloop/state/active-loop.json` (Plan 7).

For Plan 1: only handles the explicit-project case. Reads via `plugin/lib/state.sh`.
```

Create `plugin/commands/frinkloop-pause.md`:

```markdown
---
description: Pause a running FrinkLoop loop, flush state, write a handoff.
---

# /frinkloop pause <project>

(Plan 2.) Will set state.status = "paused", append a final iteration-log line, and trigger `/handoff`.

For now: print "Pause arrives in Plan 2."
```

Create `plugin/commands/frinkloop-ds.md`:

```markdown
---
description: FrinkLoop design system manager — list, create, clone, link.
---

# /frinkloop ds

(Plan 5.) Sub-routes:
- `list` — list local design systems under `~/.claude/plugins/frinkloop/design-systems/`
- `new <name>` — create a new design system (delegates to design-system-builder skill)
- `clone <url>` — extract tokens from a website
- `push <name>` — git init + push to a new GitHub repo

For now: print "Design system manager arrives in Plan 5."
```

Create `plugin/commands/frinkloop-deliver.md`:

```markdown
---
description: Run the deliverable packaging step — README, landing, screenshots, deploy, phase-2 plan.
---

# /frinkloop deliver <project>

(Plan 8.) Will run the doc-writer + screenshot-capturer subagents and the deploy step.

For now: print "Deliver arrives in Plan 8."
```

- [ ] **Step 6: Run test, expect PASS**

Run: `bats tests/plan-1/test_commands.bats`
Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```bash
git add plugin/commands/ tests/plan-1/test_commands.bats
git commit -m "feat(commands): add slash command stubs for all 7 entry points"
```

---

## Task 6: Skill placeholders (mvp-loop, design-system-builder)

**Files:**
- Create: `plugin/skills/mvp-loop/SKILL.md`
- Create: `plugin/skills/design-system-builder/SKILL.md`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_skill_stubs.bats`:

```bash
#!/usr/bin/env bats

@test "mvp-loop SKILL.md exists with frontmatter" {
  [ -f plugin/skills/mvp-loop/SKILL.md ]
  head -1 plugin/skills/mvp-loop/SKILL.md | grep -q '^---$'
  grep -q '^name:' plugin/skills/mvp-loop/SKILL.md
  grep -q '^description:' plugin/skills/mvp-loop/SKILL.md
}

@test "design-system-builder SKILL.md exists with frontmatter" {
  [ -f plugin/skills/design-system-builder/SKILL.md ]
  head -1 plugin/skills/design-system-builder/SKILL.md | grep -q '^---$'
  grep -q '^name:' plugin/skills/design-system-builder/SKILL.md
  grep -q '^description:' plugin/skills/design-system-builder/SKILL.md
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_skill_stubs.bats`
Expected: FAIL — SKILL.md files missing.

- [ ] **Step 3: Create mvp-loop placeholder**

Create `plugin/skills/mvp-loop/SKILL.md`:

```markdown
---
name: mvp-loop
description: FrinkLoop's autonomous build loop — Stop-hook spine with parallel subagent fan-out. Reads disk state, picks one task or batch, executes, verifies, logs. Use after intake-chat finishes scaffolding.
---

# mvp-loop (placeholder — implemented in Plan 2)

This skill will run the autonomous build loop per design spec §9.

For Plan 1 it is a placeholder. Invocation should print:

> "FrinkLoop build loop arrives in Plan 2. For now, you have a frozen spec and config — review them in `<project>/.frinkloop/`."
```

- [ ] **Step 4: Create design-system-builder placeholder**

Create `plugin/skills/design-system-builder/SKILL.md`:

```markdown
---
name: design-system-builder
description: Create or clone a design system for FrinkLoop. Stores tokens, components, and screenshots locally. Optionally pushes to a GitHub repo.
---

# design-system-builder (placeholder — implemented in Plan 5)

This skill will build/clone design systems per design spec §10.

For Plan 1 it is a placeholder. Invocation should print:

> "Design system builder arrives in Plan 5. For now, FrinkLoop intake will use the built-in `claude-default` preset or a stack default."
```

- [ ] **Step 5: Run test, expect PASS**

Run: `bats tests/plan-1/test_skill_stubs.bats`
Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/mvp-loop/ plugin/skills/design-system-builder/ tests/plan-1/test_skill_stubs.bats
git commit -m "feat(skills): placeholder SKILL.md for mvp-loop and design-system-builder"
```

---

## Task 7: Subagent role file placeholders

**Files:**
- Create: `plugin/agents/planner.md`, `scaffolder.md`, `builder.md`, `qa.md`, `doc-writer.md`, `screenshot-capturer.md`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_agents.bats`:

```bash
#!/usr/bin/env bats

@test "all 6 agent role files exist with frontmatter" {
  for a in planner scaffolder builder qa doc-writer screenshot-capturer; do
    [ -f "plugin/agents/$a.md" ] || (echo "missing $a.md" && false)
    head -1 "plugin/agents/$a.md" | grep -q '^---$' || (echo "no frontmatter in $a" && false)
    grep -q '^name:' "plugin/agents/$a.md" || (echo "no name in $a" && false)
    grep -q '^description:' "plugin/agents/$a.md" || (echo "no description in $a" && false)
  done
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_agents.bats`
Expected: FAIL — agent files missing.

- [ ] **Step 3: Create the 6 agent role files**

Create `plugin/agents/planner.md`:

```markdown
---
name: planner
description: FrinkLoop planner — turns spec changes into task deltas in tasks.json. Reads spec.md and current tasks.json; outputs a JSON-patch-style delta that the loop applies. Implemented in Plan 2.
---

# planner

Placeholder. Will be implemented in Plan 2.
```

Create `plugin/agents/scaffolder.md`:

```markdown
---
name: scaffolder
description: FrinkLoop scaffolder — runs giget against the chosen template and applies recipes. One-shot subagent. Implemented in Plan 3.
---

# scaffolder

Placeholder. Will be implemented in Plan 3.
```

Create `plugin/agents/builder.md`:

```markdown
---
name: builder
description: FrinkLoop builder — implements one task in a worktree. The default workhorse. Reads task spec, edits files, commits. Implemented in Plan 2.
---

# builder

Placeholder. Will be implemented in Plan 2.
```

Create `plugin/agents/qa.md`:

```markdown
---
name: qa
description: FrinkLoop QA — runs tests, typecheck, lint after each task and milestone. Writes qa.json artifact. Implemented in Plan 2.
---

# qa

Placeholder. Will be implemented in Plan 2.
```

Create `plugin/agents/doc-writer.md`:

```markdown
---
name: doc-writer
description: FrinkLoop doc-writer — generates README, JSDoc, in-code comments. Used during build and during deliverable packaging. Implemented in Plans 2/8.
---

# doc-writer

Placeholder. Will be implemented in Plans 2 and 8.
```

Create `plugin/agents/screenshot-capturer.md`:

```markdown
---
name: screenshot-capturer
description: FrinkLoop screenshot-capturer — Playwright-driven hero, feature, and mobile screen captures for landing page and README. Implemented in Plan 8.
---

# screenshot-capturer

Placeholder. Will be implemented in Plan 8.
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-1/test_agents.bats`
Expected: 1 test passes (with all 6 sub-checks).

- [ ] **Step 5: Commit**

```bash
git add plugin/agents/ tests/plan-1/test_agents.bats
git commit -m "feat(agents): placeholder role files for the 6 FrinkLoop subagents"
```

---

## Task 8: Hook placeholders (`stop.sh`, `post-iteration.sh`)

**Files:**
- Create: `plugin/hooks/stop.sh`
- Create: `plugin/hooks/post-iteration.sh`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_hooks.bats`:

```bash
#!/usr/bin/env bats

@test "stop hook is executable and exits 0" {
  [ -x plugin/hooks/stop.sh ]
  run plugin/hooks/stop.sh
  [ "$status" -eq 0 ]
}

@test "post-iteration hook is executable and exits 0" {
  [ -x plugin/hooks/post-iteration.sh ]
  run plugin/hooks/post-iteration.sh
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_hooks.bats`
Expected: FAIL — hooks missing.

- [ ] **Step 3: Create hooks**

Create `plugin/hooks/stop.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop Stop hook — placeholder.
# Plan 2 will implement: re-feed PROMPT.md to keep the loop running until DONE.
exit 0
```

Create `plugin/hooks/post-iteration.sh`:

```bash
#!/usr/bin/env bash
# FrinkLoop post-iteration hook — placeholder.
# Plan 2 will implement: append a structured iteration-log.jsonl line.
exit 0
```

Make them executable:

```bash
chmod +x plugin/hooks/stop.sh plugin/hooks/post-iteration.sh
```

- [ ] **Step 4: Run test, expect PASS**

Run: `bats tests/plan-1/test_hooks.bats`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add plugin/hooks/ tests/plan-1/test_hooks.bats
git commit -m "feat(hooks): placeholder stop.sh and post-iteration.sh"
```

---

## Task 9: Intake chat skill — templates and skill body

**Files:**
- Create: `plugin/skills/intake-chat/SKILL.md`
- Create: `plugin/skills/intake-chat/templates/spec.md.tmpl`
- Create: `plugin/skills/intake-chat/templates/config.yaml.tmpl`
- Create: `plugin/skills/intake-chat/lib/render.sh`
- Test: `tests/plan-1/test_intake_outputs.bats`

- [ ] **Step 1: Write the failing test**

Create `tests/plan-1/test_intake_outputs.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "intake render.sh exists and is executable" {
  [ -x plugin/skills/intake-chat/lib/render.sh ]
}

@test "render.sh produces a config.yaml that validates against schema" {
  cat > /tmp/answers.json <<EOF
{
  "project": "todo-mvp",
  "pitch_does": "A focused TODO list",
  "pitch_for": "ADHD professionals",
  "pitch_proves": "users add 3 items in <30 seconds",
  "pitch_makes_them_say": "I want this on my home screen",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel",
  "compression": "full",
  "exclusions": ["analytics", "auth"],
  "tdd": false
}
EOF
  run plugin/skills/intake-chat/lib/render.sh /tmp/answers.json "$FRINKLOOP_DIR"
  [ "$status" -eq 0 ]
  [ -f "$FRINKLOOP_DIR/config.yaml" ]
  [ -f "$FRINKLOOP_DIR/spec.md" ]

  # config validates
  yq -o=json "$FRINKLOOP_DIR/config.yaml" > /tmp/cfg.json
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/cfg.json --strict=false
  [ "$status" -eq 0 ]
}

@test "spec.md contains all 4 YC pitch sections" {
  cat > /tmp/answers.json <<EOF
{
  "project": "todo-mvp",
  "pitch_does": "A focused TODO list",
  "pitch_for": "ADHD professionals",
  "pitch_proves": "users add 3 items in <30 seconds",
  "pitch_makes_them_say": "I want this on my home screen",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel",
  "compression": "full",
  "exclusions": ["analytics", "auth"],
  "tdd": false
}
EOF
  plugin/skills/intake-chat/lib/render.sh /tmp/answers.json "$FRINKLOOP_DIR"
  grep -q '\*\*Does:\*\*' "$FRINKLOOP_DIR/spec.md"
  grep -q '\*\*For:\*\*' "$FRINKLOOP_DIR/spec.md"
  grep -q '\*\*MVP proves:\*\*' "$FRINKLOOP_DIR/spec.md"
  grep -q 'Done looks like' "$FRINKLOOP_DIR/spec.md"
  grep -q 'In MVP' "$FRINKLOOP_DIR/spec.md"
  grep -q 'Deferred to Phase 2' "$FRINKLOOP_DIR/spec.md"
}
```

- [ ] **Step 2: Run test, expect FAIL**

Run: `bats tests/plan-1/test_intake_outputs.bats`
Expected: FAIL — render.sh missing.

- [ ] **Step 3: Create the spec template**

Create `plugin/skills/intake-chat/templates/spec.md.tmpl`:

```markdown
# {{PROJECT}}

**Does:** {{PITCH_DOES}}
**For:** {{PITCH_FOR}}
**MVP proves:** {{PITCH_PROVES}}
**Users will say:** {{PITCH_MAKES_THEM_SAY}}

## Done looks like (testable)

{{DONE_CRITERIA}}

## In MVP

{{IN_MVP}}

## Deferred to Phase 2

{{PHASE_2}}

## Stack

- Platform: {{PLATFORM}}
- Template: {{TEMPLATE}}
- Design system: {{DESIGN_SYSTEM}}
- Deploy target: {{DEPLOY_TARGET}}

## Mode

- Mode: {{MODE}}
- HITL: {{HITL}}
- TDD: {{TDD}}
- Compression: {{COMPRESSION}}

---

*Frozen at intake on {{DATE}}. The build loop will execute against this spec.*
```

- [ ] **Step 4: Create the config template**

Create `plugin/skills/intake-chat/templates/config.yaml.tmpl`:

```yaml
schema_version: 1
project: {{PROJECT}}
mode: {{MODE}}
hitl: {{HITL}}
compression: {{COMPRESSION}}
platform: {{PLATFORM}}
template: {{TEMPLATE}}
design_system: {{DESIGN_SYSTEM}}
deploy_target: {{DEPLOY_TARGET}}
tdd: {{TDD}}
exclusions:
{{EXCLUSIONS_YAML}}
```

- [ ] **Step 5: Implement `render.sh`**

Create `plugin/skills/intake-chat/lib/render.sh`:

```bash
#!/usr/bin/env bash
# Renders intake-chat answer JSON into spec.md and config.yaml in $FRINKLOOP_DIR.
# Usage: render.sh <answers.json> <output_dir>

set -euo pipefail

ANSWERS="${1:?answers.json path required}"
OUTDIR="${2:?output dir required}"

mkdir -p "$OUTDIR"

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPL_DIR="$SKILL_DIR/templates"

# Read answers
PROJECT=$(jq -r '.project' "$ANSWERS")
PITCH_DOES=$(jq -r '.pitch_does' "$ANSWERS")
PITCH_FOR=$(jq -r '.pitch_for' "$ANSWERS")
PITCH_PROVES=$(jq -r '.pitch_proves' "$ANSWERS")
PITCH_MAKES_THEM_SAY=$(jq -r '.pitch_makes_them_say' "$ANSWERS")
MODE=$(jq -r '.mode' "$ANSWERS")
HITL=$(jq -r '.hitl' "$ANSWERS")
PLATFORM=$(jq -r '.platform' "$ANSWERS")
TEMPLATE=$(jq -r '.template' "$ANSWERS")
DESIGN_SYSTEM=$(jq -r '.design_system' "$ANSWERS")
DEPLOY_TARGET=$(jq -r '.deploy_target' "$ANSWERS")
COMPRESSION=$(jq -r '.compression' "$ANSWERS")
TDD=$(jq -r '.tdd' "$ANSWERS")
DATE=$(date -u +"%Y-%m-%d")

# Default done-criteria, in-MVP, phase-2 if not provided in answers
DONE_CRITERIA=$(jq -r '.done_criteria // ["MVP visibly demonstrates the pitch.", "Core flow completes end-to-end without errors.", "Deploys successfully to the chosen target."] | map("- [ ] " + .) | join("\n")' "$ANSWERS")
IN_MVP=$(jq -r '.in_mvp // ["Core flow described in the pitch.", "Minimal styling using the chosen design system.", "README + landing page on deliver."] | map("- " + .) | join("\n")' "$ANSWERS")
PHASE_2=$(jq -r '.exclusions | map("- " + .) | join("\n")' "$ANSWERS")
EXCLUSIONS_YAML=$(jq -r '.exclusions | map("  - " + .) | join("\n")' "$ANSWERS")

# Render spec.md
sed \
  -e "s/{{PROJECT}}/$PROJECT/g" \
  -e "s/{{PITCH_DOES}}/$PITCH_DOES/g" \
  -e "s/{{PITCH_FOR}}/$PITCH_FOR/g" \
  -e "s/{{PITCH_PROVES}}/$PITCH_PROVES/g" \
  -e "s/{{PITCH_MAKES_THEM_SAY}}/$PITCH_MAKES_THEM_SAY/g" \
  -e "s/{{PLATFORM}}/$PLATFORM/g" \
  -e "s/{{TEMPLATE}}/$TEMPLATE/g" \
  -e "s/{{DESIGN_SYSTEM}}/$DESIGN_SYSTEM/g" \
  -e "s/{{DEPLOY_TARGET}}/$DEPLOY_TARGET/g" \
  -e "s/{{MODE}}/$MODE/g" \
  -e "s/{{HITL}}/$HITL/g" \
  -e "s/{{TDD}}/$TDD/g" \
  -e "s/{{COMPRESSION}}/$COMPRESSION/g" \
  -e "s/{{DATE}}/$DATE/g" \
  "$TMPL_DIR/spec.md.tmpl" > "$OUTDIR/spec.md.partial"

# Multi-line substitutions (sed-unsafe — use awk)
awk -v done_c="$DONE_CRITERIA" -v in_mvp="$IN_MVP" -v phase2="$PHASE_2" '
  { gsub(/\{\{DONE_CRITERIA\}\}/, done_c); gsub(/\{\{IN_MVP\}\}/, in_mvp); gsub(/\{\{PHASE_2\}\}/, phase2); print }
' "$OUTDIR/spec.md.partial" > "$OUTDIR/spec.md"
rm "$OUTDIR/spec.md.partial"

# Render config.yaml
sed \
  -e "s/{{PROJECT}}/$PROJECT/g" \
  -e "s/{{MODE}}/$MODE/g" \
  -e "s/{{HITL}}/$HITL/g" \
  -e "s/{{COMPRESSION}}/$COMPRESSION/g" \
  -e "s/{{PLATFORM}}/$PLATFORM/g" \
  -e "s/{{TEMPLATE}}/$TEMPLATE/g" \
  -e "s/{{DESIGN_SYSTEM}}/$DESIGN_SYSTEM/g" \
  -e "s/{{DEPLOY_TARGET}}/$DEPLOY_TARGET/g" \
  -e "s/{{TDD}}/$TDD/g" \
  "$TMPL_DIR/config.yaml.tmpl" > "$OUTDIR/config.yaml.partial"

awk -v excl="$EXCLUSIONS_YAML" '
  { gsub(/\{\{EXCLUSIONS_YAML\}\}/, excl); print }
' "$OUTDIR/config.yaml.partial" > "$OUTDIR/config.yaml"
rm "$OUTDIR/config.yaml.partial"

echo "Rendered: $OUTDIR/spec.md and $OUTDIR/config.yaml"
```

Make it executable: `chmod +x plugin/skills/intake-chat/lib/render.sh`.

- [ ] **Step 6: Create `intake-chat/SKILL.md`**

Create `plugin/skills/intake-chat/SKILL.md`:

````markdown
---
name: intake-chat
description: FrinkLoop intake chat — a 9-step YC-shaped clarifier that turns a project idea into a frozen spec.md and config.yaml. Run with compression off (user-facing). Output goes to <project>/.frinkloop/.
---

# intake-chat

Run a structured 9-step conversation with the user to produce a frozen spec.md and config.yaml.

## Compression

Always run with caveman compression **off** during this skill — output is user-facing and needs natural prose.

## Steps (one question per turn)

### 1. YC pitch (4 sub-questions)

Ask in order, one per turn:
- "What does it do?" — capture as `pitch_does` (1 sentence).
- "Who is this for? Be specific." — capture as `pitch_for`.
- "What's the smallest version that proves it works?" — capture as `pitch_proves`.
- "What would make a user say 'I want this'?" — capture as `pitch_makes_them_say`.

### 2. Mode

Ask: "Hackathon demo, Commercial MVP, or Internal demo?" — capture as `mode` ∈ {hackathon, commercial, internal-demo}.

### 3. HITL level

Ask: "How human-in-the-loop? Fully autonomous, milestone checkpoints, or flag-on-blocker only?" — capture as `hitl`.

### 4. Platform & deploy target

Auto-suggest from the pitch (use the platform → registry mapping in `plugin/templates/registry.yaml`). Ask user to confirm or override. Capture as `platform` and `deploy_target`.

### 5. Stack preference

Ask: "Pick a recipe yourself, or shall I use the default for `<platform>`?"
- "I pick" → list options from `registry.yaml`, capture choice as `template`.
- "You choose" → use registry default for that platform.

### 6. Design system

List local design systems under `~/.claude/plugins/frinkloop/design-systems/` plus the built-in `claude-default`. Offer:
- *Use existing* (pick by name) → capture name
- *Clone URL or brand* → defer to `design-system-builder` (Plan 5; for Plan 1, fall back to `claude-default` and note in decisions.md)
- *Create new* → defer to `design-system-builder` (same Plan 1 fallback)
- *Use stack default* → "tailwind-shadcn-defaults"

### 7. Hard exclusions

State: "By default, FrinkLoop excludes from MVP: real auth, payments, real user data, production observability, custom infra. Anything to add or remove?"

User can append. With explicit warning, can remove. Final list goes to `exclusions`.

### 8. Spec proposal

Synthesize: produce a draft of done-criteria (3–5 testable bullets derived from `pitch_proves` + `pitch_makes_them_say`), in-MVP bullets, and phase-2 bullets (= exclusions + ambitious-but-not-needed items). Present to user as a proposal. Edit inline based on user feedback.

### 9. Final approve

When user says "go", invoke the renderer:

```bash
plugin/skills/intake-chat/lib/render.sh /tmp/frinkloop-answers-$$.json "$PROJECT_DIR/.frinkloop"
```

Where the answers JSON has all captured fields:

```json
{
  "project": "...",
  "pitch_does": "...",
  "pitch_for": "...",
  "pitch_proves": "...",
  "pitch_makes_them_say": "...",
  "mode": "...",
  "hitl": "...",
  "compression": "full",
  "platform": "...",
  "template": "...",
  "design_system": "...",
  "deploy_target": "...",
  "tdd": false,
  "exclusions": ["..."],
  "done_criteria": ["...", "..."],
  "in_mvp": ["...", "..."]
}
```

After render succeeds:
- For Plan 1: stop here. Tell the user: "Spec written to `<project>/.frinkloop/spec.md` and config to `<project>/.frinkloop/config.yaml`. The build loop arrives in Plan 2."
- For Plan 2 onward: hand off to `mvp-loop` skill.

## Pre-fill from learning profile

If `~/.claude/plugins/frinkloop/learning/profile.json` exists, pre-fill defaults:
- `preferred_hitl` → default for step 3
- `preferred_stacks[<platform>]` → default for step 5
- `default_exclusions_added` → suggested adds at step 7
- `design_system_default` → default for step 6

(Implemented in Plan 6; for Plan 1, skip this section.)
````

- [ ] **Step 7: Run test, expect PASS**

Run: `bats tests/plan-1/test_intake_outputs.bats`

Expected: 3 tests pass.

If `yq` is not installed, install it: `brew install yq` (macOS) or `pip install yq`.

- [ ] **Step 8: Commit**

```bash
git add plugin/skills/intake-chat/ tests/plan-1/test_intake_outputs.bats
git commit -m "feat(intake): YC-shaped 9-step intake chat skill with template renderer"
```

---

## Task 10: Repo housekeeping (root README pointer, commit hygiene)

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read the current root README**

Run: `cat README.md`

- [ ] **Step 2: Replace it with a pointer to the plugin and the design**

Replace `README.md` contents with:

```markdown
# FrinkLoop

> Autonomous MVP development for Claude Code.

This repo contains the **FrinkLoop plugin** for Claude Code.

## Plugin

See [`plugin/README.md`](plugin/README.md) for installation and usage.

## Design

- Spec: [`docs/superpowers/specs/2026-04-30-frinkloop-plugin-redesign-design.md`](docs/superpowers/specs/2026-04-30-frinkloop-plugin-redesign-design.md)
- Roadmap: [`docs/superpowers/plans/2026-04-30-frinkloop-roadmap.md`](docs/superpowers/plans/2026-04-30-frinkloop-roadmap.md)

## History

The previous Python-based FrinkLoop framework lived at this path through commit `8dde005 v3` (2026-04-06). It has been superseded by the plugin redesign.

## License

MIT
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: repoint root README to the plugin and design spec"
```

---

## Task 11: Plan-1 integration smoke test

**Files:**
- Create: `tests/plan-1/test_e2e.bats`

- [ ] **Step 1: Write the integration test**

Create `tests/plan-1/test_e2e.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/demo-project"
  mkdir -p "$PROJECT_DIR/.frinkloop"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "end-to-end Plan 1 smoke: render spec + config from answers, validate, state init works" {
  cat > /tmp/answers-e2e.json <<EOF
{
  "project": "demo-project",
  "pitch_does": "A live briefing instrument for creative agencies",
  "pitch_for": "agency planners pre-meeting",
  "pitch_proves": "user can run a full 5-min briefing flow without confusion",
  "pitch_makes_them_say": "I want this in every weekly review",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel",
  "compression": "full",
  "exclusions": ["analytics", "auth", "real-user-data"],
  "tdd": false
}
EOF

  # Step 1: render the spec + config
  plugin/skills/intake-chat/lib/render.sh /tmp/answers-e2e.json "$PROJECT_DIR/.frinkloop"
  [ -f "$PROJECT_DIR/.frinkloop/spec.md" ]
  [ -f "$PROJECT_DIR/.frinkloop/config.yaml" ]

  # Step 2: validate config against schema
  yq -o=json "$PROJECT_DIR/.frinkloop/config.yaml" > /tmp/cfg-e2e.json
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/cfg-e2e.json --strict=false
  [ "$status" -eq 0 ]

  # Step 3: state_init produces a valid state.json
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  source plugin/lib/state.sh
  state_init main
  [ -f "$FRINKLOOP_DIR/state.json" ]

  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d "$FRINKLOOP_DIR/state.json" --strict=false
  [ "$status" -eq 0 ]

  # Step 4: log_iteration writes a JSONL line
  log_iteration '{"event":"intake_done","project":"demo-project"}'
  [ -f "$FRINKLOOP_DIR/iteration-log.jsonl" ]
  run wc -l < "$FRINKLOOP_DIR/iteration-log.jsonl"
  [ "$output" -eq 1 ]
}
```

- [ ] **Step 2: Run test, expect PASS**

Run: `bats tests/plan-1/test_e2e.bats`
Expected: 1 test passes (with all 4 sub-checks).

- [ ] **Step 3: Run the full test suite**

Run: `bats tests/`
Expected: all tests across all task files pass.

- [ ] **Step 4: Commit**

```bash
git add tests/plan-1/test_e2e.bats
git commit -m "test(plan-1): end-to-end smoke verifying intake render + state init"
```

---

## Task 12: Tag end-of-plan

- [ ] **Step 1: Tag the commit**

```bash
git tag -a frinkloop-plan-1-done -m "Plan 1 complete: plugin foundation + intake-chat skill"
```

- [ ] **Step 2: Final verification**

Run: `bats tests/`
Expected: all tests pass.

Then a final manual check by listing the plugin tree:

```bash
tree plugin -L 2
```

Expected output structure (counts approximate):
- `plugin/plugin.json`
- `plugin/README.md`
- `plugin/commands/` with 7 `.md` files
- `plugin/skills/intake-chat/`, `plugin/skills/mvp-loop/`, `plugin/skills/design-system-builder/`
- `plugin/agents/` with 6 `.md` files
- `plugin/hooks/` with 2 `.sh` files
- `plugin/lib/state.sh` and `plugin/lib/schemas/*.schema.json`

---

## Self-Review (post-plan)

**Spec coverage check:**

| Spec section | Where in this plan |
|---|---|
| §6 plugin layout | Tasks 1, 5, 6, 7, 8 (commands, skills, agents, hooks all stubbed) |
| §7 slash command surface | Task 5 (all 7 commands) |
| §8 intake chat flow | Task 9 (intake-chat skill body + renderer) |
| §9 build loop | NOT in this plan — Plan 2 |
| §10 design system store | NOT in this plan — Plan 5 (placeholder skill in Task 6) |
| §11 local learning | NOT in this plan — Plan 6 (referenced in intake skill but skipped) |
| §12 quota resume | NOT in this plan — Plan 7 |
| §13 privacy | Task 1 (plugin README states it) |
| §14 deliverables | NOT in this plan — Plan 8 |
| §15 template registry | NOT in this plan — Plan 3 (only referenced in intake skill prose) |
| YC framework | Task 9 (4 pitch questions baked into intake skill) |

Plan 1 explicitly defers loop, templates, design systems, learning, quota resume, and deliverables to later plans. This plan ships a working intake that produces frozen spec + config and a tested state-helper library.

**Placeholder scan:** Searched for "TODO", "TBD", "implement later", "fill in details" — none present in the plan steps themselves. References to "Plan 2/3/5/6/7/8" are intentional cross-plan deferrals, not placeholders.

**Type consistency:**
- `state.json` field names: `schema_version, current_milestone, current_task, iteration_count, branch, last_verified_sha, status` — used identically in Task 3 schema, Task 4 helpers, Task 11 e2e.
- `config.yaml` fields: `schema_version, project, mode, hitl, compression, platform, template, design_system, deploy_target, tdd, exclusions` — used identically across Task 3 schema, Task 9 templates/renderer, and Task 11 e2e fixtures.
- enums (mode, hitl, platform, compression, deploy_target) — values consistent across schema and renderer.

**Minor caveat acknowledged:** the renderer's `sed`-based templating is fragile against pitch text containing `/` or `&`. Plan 9 (polish) should harden this — either move to `mustache`/`gomplate`, or pre-escape user input. For Plan 1's hackathon-mode use it's acceptable.

---

*End of Plan 1.*
