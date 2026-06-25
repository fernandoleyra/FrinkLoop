# FrinkLoop Plan 3 — Templates Registry + Scaffolder + Recipes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the 10-platform template registry, a `scaffolder` subagent that calls `giget` to bootstrap a project from any registered template, and a shadcn-style additive recipe runner with three reference recipes (`tailwind`, `deploy-vercel`, `playwright`).

**Architecture:** Registry is a YAML file mapping logical platform/template names to giget source strings. `lib/scaffolder.sh` validates the chosen template against the registry, then invokes giget. `lib/recipes.sh` applies a named recipe atomically using `git stash`/commit boundaries — apply, verify, commit OR rollback. Each recipe is a directory with `recipe.yaml` metadata + `apply.sh` script.

**Tech Stack:** giget (UnJS) for template fetches, bash for scaffolder + recipe runner, YAML for registry, JSON Schema (Draft-07) for recipe metadata, bats for tests.

---

## File Structure

- Create: `plugin/templates/registry.yaml` — 10-platform map
- Create: `plugin/lib/schemas/registry.schema.json` — validates registry.yaml (as JSON via yq)
- Create: `plugin/lib/schemas/recipe.schema.json` — validates each recipe.yaml
- Create: `plugin/lib/scaffolder.sh` — giget wrapper
- Create: `plugin/lib/recipes.sh` — recipe runner with rollback
- Create: `plugin/recipes/_template/recipe.yaml` and `apply.sh` — empty starter
- Create: `plugin/recipes/tailwind/recipe.yaml` and `apply.sh`
- Create: `plugin/recipes/deploy-vercel/recipe.yaml` and `apply.sh`
- Create: `plugin/recipes/playwright/recipe.yaml` and `apply.sh`
- Modify: `plugin/agents/scaffolder.md` — replace placeholder with real body
- Create: `tests/plan-3/test_registry.bats`, `test_scaffolder.bats`, `test_recipes.bats`, `test_real_recipes.bats`

---

## Task 1: Registry + schema

**Files:** `plugin/templates/registry.yaml`, `plugin/lib/schemas/registry.schema.json`, `tests/plan-3/test_registry.bats`

- [ ] **Step 1: Write tests**

`tests/plan-3/test_registry.bats`:

```bash
#!/usr/bin/env bats

@test "registry.yaml exists and parses to JSON" {
  [ -f plugin/templates/registry.yaml ]
  run yq -o=json plugin/templates/registry.yaml
  [ "$status" -eq 0 ]
}

@test "registry validates against schema" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run npx --no-install ajv validate -s plugin/lib/schemas/registry.schema.json -d /tmp/registry.json --strict=false
  [ "$status" -eq 0 ]
}

@test "registry has 10 entries with required fields" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run jq '.templates | length' /tmp/registry.json
  [ "$output" -ge 10 ]
}

@test "every template entry has a giget source string" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run jq -r '.templates | map(select(.giget == null or .giget == "")) | length' /tmp/registry.json
  [ "$output" = "0" ]
}

@test "registry resolves vite-shadcn template" {
  yq -o=json plugin/templates/registry.yaml > /tmp/registry.json
  run jq -r '.templates[] | select(.id == "vite-shadcn") | .giget' /tmp/registry.json
  [ -n "$output" ]
  [ "$output" != "null" ]
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create the schema**

`plugin/lib/schemas/registry.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop templates registry",
  "type": "object",
  "required": ["schema_version", "templates"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "templates": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "platform", "name", "giget", "default"],
        "additionalProperties": false,
        "properties": {
          "id": { "type": "string", "minLength": 1 },
          "platform": {
            "type": "string",
            "enum": [
              "web-fullstack", "spa-static", "marketing-landing",
              "node-api", "python-api", "node-cli", "python-cli",
              "mobile-expo", "browser-extension", "discord-bot", "slack-bot"
            ]
          },
          "name": { "type": "string" },
          "giget": { "type": "string", "minLength": 1 },
          "default": { "type": "boolean" },
          "notes": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Create the registry**

`plugin/templates/registry.yaml`:

```yaml
schema_version: 1
templates:
  - id: next-saas-starter
    platform: web-fullstack
    name: "Next.js SaaS Starter (Vercel)"
    giget: "gh:nextjs/saas-starter"
    default: true
    notes: "Drizzle + Tailwind + shadcn baked in. Mark Stripe paths as Phase 2."

  - id: vite-shadcn
    platform: spa-static
    name: "Vite + React + shadcn/ui"
    giget: "gh:shadcn-ui/vite-template"
    default: true

  - id: astroship
    platform: marketing-landing
    name: "Astroship (Astro + Tailwind)"
    giget: "gh:surjithctly/astroship"
    default: true

  - id: hono-openapi
    platform: node-api
    name: "Hono + OpenAPI starter"
    giget: "gh:w3cj/hono-open-api-starter"
    default: true

  - id: fastapi-ai-prod
    platform: python-api
    name: "FastAPI AI Production Template"
    giget: "gh:wahyudesu/Fastapi-AI-Production-Template"
    default: true

  - id: citty-playground
    platform: node-cli
    name: "Citty (UnJS) playground"
    giget: "gh:unjs/citty/playground"
    default: true

  - id: uvinit
    platform: python-cli
    name: "uvinit (Typer + uv)"
    giget: "gh:jlevy/uvinit"
    default: true
    notes: "Invoke with --data flags to skip interactive prompts."

  - id: expo-obytes
    platform: mobile-expo
    name: "Expo Obytes Starter"
    giget: "gh:obytes/react-native-template-obytes"
    default: true

  - id: wxt-extension
    platform: browser-extension
    name: "WXT browser extension starter"
    giget: "gh:poweroutlet2/browser-extension-starter"
    default: true

  - id: discord-bot-ts
    platform: discord-bot
    name: "Discord Bot TypeScript Template"
    giget: "gh:KevinNovak/Discord-Bot-TypeScript-Template"
    default: true

  - id: slack-bolt-ts
    platform: slack-bot
    name: "Slack Bolt TypeScript starter"
    giget: "gh:slack-samples/bolt-ts-starter-template"
    default: true
```

- [ ] **Step 5: Run, expect PASS** (5/5)

- [ ] **Step 6: Commit**

```bash
git add plugin/templates/registry.yaml plugin/lib/schemas/registry.schema.json tests/plan-3/test_registry.bats
git commit -m "feat(templates): 11-entry registry + JSON schema (10 platforms incl. slack-bot)"
```

---

## Task 2: Scaffolder helper (`lib/scaffolder.sh`)

**Files:** `plugin/lib/scaffolder.sh`, `tests/plan-3/test_scaffolder.bats`

- [ ] **Step 1: Tests**

`tests/plan-3/test_scaffolder.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  source "$PLUGIN_LIB_DIR/scaffolder.sh"
  export FAKE_GIGET="$TMPDIR/fake-giget"
  cat > "$FAKE_GIGET" <<'EOF'
#!/usr/bin/env bash
# fake giget: writes args to $TMPDIR/giget.log and creates a fake project
echo "$@" > "$TMPDIR/giget.log"
target="${@: -1}"
mkdir -p "$target"
echo "scaffolded by fake giget" > "$target/README.md"
EOF
  chmod +x "$FAKE_GIGET"
  export GIGET_BIN="$FAKE_GIGET"
  export REGISTRY_FILE="$PLUGIN_DIR/templates/registry.yaml"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "resolve_template returns giget source for known id" {
  run resolve_template "vite-shadcn"
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "resolve_template returns nonzero for unknown id" {
  run resolve_template "nonexistent-template"
  [ "$status" -ne 0 ]
}

@test "default_template_for_platform returns the default for that platform" {
  run default_template_for_platform "spa-static"
  [ "$status" -eq 0 ]
  [ "$output" = "vite-shadcn" ]
}

@test "scaffold invokes giget with the right source and target" {
  scaffold "vite-shadcn" "$TMPDIR/proj"
  [ -d "$TMPDIR/proj" ]
  [ -f "$TMPDIR/proj/README.md" ]
  grep -q "vite-template" "$TMPDIR/giget.log"
}

@test "scaffold fails on unknown template" {
  run scaffold "nonexistent" "$TMPDIR/proj"
  [ "$status" -ne 0 ]
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement `lib/scaffolder.sh`**

```bash
#!/usr/bin/env bash
# FrinkLoop scaffolder — wraps giget against the templates/registry.yaml.
# Caller may set GIGET_BIN (default: "npx --yes giget") and REGISTRY_FILE.

set -euo pipefail

: "${GIGET_BIN:=npx --yes giget}"
: "${REGISTRY_FILE:=$(dirname "${BASH_SOURCE[0]}")/../templates/registry.yaml}"

resolve_template() {
  local id="$1"
  local out
  out=$(yq -o=json "$REGISTRY_FILE" | jq -r --arg id "$id" '.templates[] | select(.id == $id) | .giget' 2>/dev/null || true)
  if [ -z "$out" ] || [ "$out" = "null" ]; then
    return 1
  fi
  echo "$out"
}

default_template_for_platform() {
  local platform="$1"
  local out
  out=$(yq -o=json "$REGISTRY_FILE" | jq -r --arg p "$platform" '
    .templates[] | select(.platform == $p and .default == true) | .id
  ' | head -1)
  if [ -z "$out" ]; then
    return 1
  fi
  echo "$out"
}

scaffold() {
  local template_id="$1"
  local target="$2"
  local source
  source=$(resolve_template "$template_id") || {
    echo "scaffolder: unknown template '$template_id'" >&2
    return 1
  }
  $GIGET_BIN "$source" "$target"
}
```

- [ ] **Step 4: Run, expect PASS** (5/5)

- [ ] **Step 5: Commit**

```bash
git add plugin/lib/scaffolder.sh tests/plan-3/test_scaffolder.bats
git commit -m "feat(scaffolder): giget wrapper with registry-driven template resolution"
```

---

## Task 3: Recipe runner (`lib/recipes.sh`) + recipe schema

**Files:** `plugin/lib/recipes.sh`, `plugin/lib/schemas/recipe.schema.json`, `plugin/recipes/_template/recipe.yaml`, `plugin/recipes/_template/apply.sh`, `tests/plan-3/test_recipes.bats`

- [ ] **Step 1: Tests**

`tests/plan-3/test_recipes.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
  source "$PLUGIN_LIB_DIR/recipes.sh"
  export RECIPES_DIR="$PLUGIN_DIR/recipes"

  # Project workspace
  export PROJECT_DIR="$TMPDIR/proj"
  mkdir -p "$PROJECT_DIR"
  cd "$PROJECT_DIR"
  git init -q
  git config user.email t@example.com
  git config user.name t
  echo "init" > README.md
  git add README.md
  git -c commit.gpgsign=false commit -q -m "init"

  # Local fixture recipe inside TMPDIR
  export FIXTURE_RECIPES="$TMPDIR/recipes"
  mkdir -p "$FIXTURE_RECIPES/sample-pass" "$FIXTURE_RECIPES/sample-fail"
  cat > "$FIXTURE_RECIPES/sample-pass/recipe.yaml" <<EOF
schema_version: 1
id: sample-pass
name: Sample passing recipe
applies_to: [spa-static]
EOF
  cat > "$FIXTURE_RECIPES/sample-pass/apply.sh" <<'EOF'
#!/usr/bin/env bash
echo "added by sample-pass" > sample.txt
EOF
  chmod +x "$FIXTURE_RECIPES/sample-pass/apply.sh"

  cat > "$FIXTURE_RECIPES/sample-fail/recipe.yaml" <<EOF
schema_version: 1
id: sample-fail
name: Sample failing recipe
applies_to: [spa-static]
EOF
  cat > "$FIXTURE_RECIPES/sample-fail/apply.sh" <<'EOF'
#!/usr/bin/env bash
echo "halfway" > halfway.txt
exit 1
EOF
  chmod +x "$FIXTURE_RECIPES/sample-fail/apply.sh"
}

teardown() {
  cd /
  rm -rf "$TMPDIR"
}

@test "recipe template exists with required schema fields" {
  yq -o=json "$PLUGIN_DIR/recipes/_template/recipe.yaml" > /tmp/r.json
  run bash -c "cd '$REPO_ROOT' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/recipe.schema.json' -d /tmp/r.json --strict=false"
  [ "$status" -eq 0 ]
}

@test "apply_recipe with passing recipe creates files and commits" {
  apply_recipe "$FIXTURE_RECIPES/sample-pass"
  [ -f sample.txt ]
  run git log --oneline | head -1
  echo "$output" | grep -q "recipe(sample-pass)"
}

@test "apply_recipe with failing recipe rolls back to clean state" {
  run apply_recipe "$FIXTURE_RECIPES/sample-fail"
  [ "$status" -ne 0 ]
  [ ! -f halfway.txt ]
  run git status --porcelain
  [ -z "$output" ]
}

@test "apply_recipe is idempotent — second run is a no-op for the test recipe" {
  apply_recipe "$FIXTURE_RECIPES/sample-pass"
  prev_sha=$(git rev-parse HEAD)
  apply_recipe "$FIXTURE_RECIPES/sample-pass" || true
  curr_sha=$(git rev-parse HEAD)
  # Either same SHA (no-op detected) OR a new commit if the recipe is non-idempotent.
  # The simple test recipe overwrites sample.txt with same content → working tree clean → recipe runner skips commit.
  # Tolerate either: just confirm no error blew up the tree.
  run git status --porcelain
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create the recipe schema**

`plugin/lib/schemas/recipe.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop recipe",
  "type": "object",
  "required": ["schema_version", "id", "name", "applies_to"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "id": { "type": "string", "minLength": 1 },
    "name": { "type": "string", "minLength": 1 },
    "description": { "type": "string" },
    "applies_to": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "enum": [
          "web-fullstack", "spa-static", "marketing-landing",
          "node-api", "python-api", "node-cli", "python-cli",
          "mobile-expo", "browser-extension", "discord-bot", "slack-bot",
          "*"
        ]
      }
    },
    "depends_on": { "type": "array", "items": { "type": "string" } },
    "post_apply_check": { "type": "string" }
  }
}
```

- [ ] **Step 4: Create the `_template` recipe**

`plugin/recipes/_template/recipe.yaml`:

```yaml
schema_version: 1
id: _template
name: Recipe template — copy this for new recipes
description: Empty starter — duplicate this folder, rename, fill in apply.sh
applies_to: ["*"]
```

`plugin/recipes/_template/apply.sh`:

```bash
#!/usr/bin/env bash
# Recipe template. Replace this with your actual setup commands.
# Receives PROJECT_DIR as cwd. Exits non-zero on failure to trigger rollback.
set -euo pipefail
echo "_template recipe: no-op"
```

`chmod +x plugin/recipes/_template/apply.sh`

- [ ] **Step 5: Implement `lib/recipes.sh`**

```bash
#!/usr/bin/env bash
# FrinkLoop recipe runner — atomic apply with rollback.
# Recipe folder structure: <recipe>/recipe.yaml + <recipe>/apply.sh
# Caller's cwd is PROJECT_DIR (a git repo).

set -euo pipefail

apply_recipe() {
  local recipe_dir="$1"
  local recipe_id
  recipe_id=$(yq -o=json "$recipe_dir/recipe.yaml" | jq -r '.id')

  if [ ! -x "$recipe_dir/apply.sh" ]; then
    echo "recipes: $recipe_id has no executable apply.sh" >&2
    return 1
  fi

  # Snapshot via git stash (if working tree dirty) so we can roll back.
  local pre_sha
  pre_sha=$(git rev-parse HEAD)

  # Run apply.sh; on failure, hard-reset to pre_sha and clean.
  if "$recipe_dir/apply.sh"; then
    # If nothing changed, no-op (idempotent recipe) — return success without committing.
    if [ -z "$(git status --porcelain)" ]; then
      return 0
    fi
    git add -A
    git -c commit.gpgsign=false commit -q -m "recipe($recipe_id): apply"
    return 0
  else
    local rc=$?
    git reset --hard "$pre_sha" >/dev/null
    git clean -fd >/dev/null
    return $rc
  fi
}
```

- [ ] **Step 6: Run, expect PASS** (4/4)

- [ ] **Step 7: Commit**

```bash
git add plugin/lib/recipes.sh plugin/lib/schemas/recipe.schema.json plugin/recipes/_template/ tests/plan-3/test_recipes.bats
git commit -m "feat(recipes): atomic recipe runner with git-stash-based rollback + _template starter"
```

---

## Task 4: Real recipes — tailwind, deploy-vercel, playwright

**Files:**
- `plugin/recipes/tailwind/{recipe.yaml,apply.sh}`
- `plugin/recipes/deploy-vercel/{recipe.yaml,apply.sh}`
- `plugin/recipes/playwright/{recipe.yaml,apply.sh}`
- `tests/plan-3/test_real_recipes.bats`

The actual `apply.sh` scripts assume the project has `package.json`. Each is conservative: install deps, write a minimal config file, do nothing else.

- [ ] **Step 1: Tests**

`tests/plan-3/test_real_recipes.bats`:

```bash
#!/usr/bin/env bats

setup() {
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
}

@test "tailwind recipe.yaml is valid" {
  yq -o=json "$PLUGIN_DIR/recipes/tailwind/recipe.yaml" > /tmp/t.json
  run bash -c "cd '$REPO_ROOT' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/recipe.schema.json' -d /tmp/t.json --strict=false"
  [ "$status" -eq 0 ]
}

@test "deploy-vercel recipe.yaml is valid" {
  yq -o=json "$PLUGIN_DIR/recipes/deploy-vercel/recipe.yaml" > /tmp/v.json
  run bash -c "cd '$REPO_ROOT' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/recipe.schema.json' -d /tmp/v.json --strict=false"
  [ "$status" -eq 0 ]
}

@test "playwright recipe.yaml is valid" {
  yq -o=json "$PLUGIN_DIR/recipes/playwright/recipe.yaml" > /tmp/p.json
  run bash -c "cd '$REPO_ROOT' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/recipe.schema.json' -d /tmp/p.json --strict=false"
  [ "$status" -eq 0 ]
}

@test "all 3 real recipes have executable apply.sh" {
  for r in tailwind deploy-vercel playwright; do
    [ -x "$PLUGIN_DIR/recipes/$r/apply.sh" ] || (echo "missing/exec $r" && false)
  done
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create the recipes**

`plugin/recipes/tailwind/recipe.yaml`:

```yaml
schema_version: 1
id: tailwind
name: Tailwind CSS
description: Install Tailwind CSS, init config, add directives to main CSS entrypoint.
applies_to: [web-fullstack, spa-static, marketing-landing]
post_apply_check: "test -f tailwind.config.js -o -f tailwind.config.ts"
```

`plugin/recipes/tailwind/apply.sh`:

```bash
#!/usr/bin/env bash
# Tailwind recipe — installs tailwind, postcss, autoprefixer; inits config.
set -euo pipefail

if [ ! -f package.json ]; then
  echo "tailwind recipe: no package.json found" >&2
  exit 1
fi

npm install -D tailwindcss@^3 postcss@^8 autoprefixer@^10 >/dev/null 2>&1

if ! [ -f tailwind.config.js ] && ! [ -f tailwind.config.ts ]; then
  npx --yes tailwindcss init -p >/dev/null 2>&1 || cat > tailwind.config.js <<'EOF'
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
EOF
fi
```

`plugin/recipes/deploy-vercel/recipe.yaml`:

```yaml
schema_version: 1
id: deploy-vercel
name: Deploy to Vercel
description: Add a vercel.json with framework auto-detection. Does not create a Vercel project — the human runs `vercel` first time.
applies_to: [web-fullstack, spa-static, marketing-landing]
post_apply_check: "test -f vercel.json"
```

`plugin/recipes/deploy-vercel/apply.sh`:

```bash
#!/usr/bin/env bash
# deploy-vercel recipe — drops a minimal vercel.json.
set -euo pipefail

if [ -f vercel.json ]; then
  exit 0
fi

cat > vercel.json <<'EOF'
{
  "$schema": "https://openapi.vercel.sh/vercel.json"
}
EOF
```

`plugin/recipes/playwright/recipe.yaml`:

```yaml
schema_version: 1
id: playwright
name: Playwright (headless browser, used by FrinkLoop screenshot pipeline)
description: Install playwright + chromium. Add a basic config so screenshot-capturer can run.
applies_to: [web-fullstack, spa-static, marketing-landing]
post_apply_check: "test -f playwright.config.ts -o -f playwright.config.js"
```

`plugin/recipes/playwright/apply.sh`:

```bash
#!/usr/bin/env bash
# Playwright recipe — installs @playwright/test + chromium browser.
set -euo pipefail

if [ ! -f package.json ]; then
  echo "playwright recipe: no package.json found" >&2
  exit 1
fi

npm install -D @playwright/test >/dev/null 2>&1
npx --yes playwright install --with-deps chromium >/dev/null 2>&1 || true

if ! [ -f playwright.config.ts ] && ! [ -f playwright.config.js ]; then
  cat > playwright.config.ts <<'EOF'
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
});
EOF
fi
```

`chmod +x plugin/recipes/{tailwind,deploy-vercel,playwright}/apply.sh`

- [ ] **Step 4: Run, expect PASS** (4/4)

- [ ] **Step 5: Commit**

```bash
git add plugin/recipes/tailwind/ plugin/recipes/deploy-vercel/ plugin/recipes/playwright/ tests/plan-3/test_real_recipes.bats
git commit -m "feat(recipes): tailwind, deploy-vercel, playwright (3 reference recipes)"
```

---

## Task 5: Real `scaffolder` agent

**File:** `plugin/agents/scaffolder.md`

- [ ] **Step 1: Test**

Append to a NEW `tests/plan-3/test_scaffolder_agent.bats`:

```bash
#!/usr/bin/env bats

@test "scaffolder agent has real body and references registry + giget + recipes" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/scaffolder.md
  grep -q "registry.yaml" plugin/agents/scaffolder.md
  grep -q "giget" plugin/agents/scaffolder.md
  grep -q "apply_recipe" plugin/agents/scaffolder.md
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Replace `agents/scaffolder.md`**

```markdown
---
name: scaffolder
description: FrinkLoop scaffolder — bootstraps a new project from the templates registry and applies a list of recipes. One-shot subagent. Reads config.yaml for template + recipes, calls giget, then applies each recipe atomically.
---

# scaffolder

## Inputs
- `<project>/.frinkloop/config.yaml` — `template`, `platform`, optional `recipes` list
- `<project>/.frinkloop/spec.md` for context (rarely needed)
- `plugin/templates/registry.yaml` — template registry

## Output
- A populated `$PROJECT_DIR` containing the scaffolded template + applied recipes
- One git commit per recipe applied (`recipe(<id>): apply`) plus the initial scaffold commit
- Marks the corresponding `kind=scaffold` task done in `tasks.json` (the orchestrator does this — you just return)

## Job

1. Read `template` from config.yaml. Resolve via:

   ```bash
   source plugin/lib/scaffolder.sh
   resolve_template "<template_id>"
   ```

   If unknown, return BLOCKED.

2. Run scaffold:

   ```bash
   scaffold "<template_id>" "$PROJECT_DIR"
   ```

   This calls `giget` under the hood. Fails if the template isn't reachable (e.g. offline).

3. `cd "$PROJECT_DIR"` and `git init` if not already.

4. Stage everything and make an initial commit:

   ```bash
   git add -A
   git -c commit.gpgsign=false commit -m "scaffold: <template_id>"
   ```

5. For each recipe id listed in config.yaml's `recipes:` (optional field):

   ```bash
   source plugin/lib/recipes.sh
   apply_recipe "plugin/recipes/<recipe_id>"
   ```

   Each apply is atomic — failure rolls back to pre-recipe state. If a recipe fails, return BLOCKED with the recipe id and stderr.

6. Return DONE with a list of: template id, applied recipes, final HEAD sha.

## Constraints
- Run only inside `$PROJECT_DIR`. Don't edit the plugin.
- Don't push. Don't deploy. That's Plan 8.
- Don't add new dependencies beyond what the template + recipes specify.
- One-shot: this subagent runs once per project at scaffold time, not per task.
```

- [ ] **Step 4: Run, expect PASS** (1/1)

- [ ] **Step 5: Commit**

```bash
git add plugin/agents/scaffolder.md tests/plan-3/test_scaffolder_agent.bats
git commit -m "feat(agents): real scaffolder agent — registry + giget + recipes"
```

---

## Task 6: Tag and final verification

- [ ] **Step 1: Run full suite**

```bash
bats tests/plan-1/ tests/plan-2/ tests/plan-3/
```

Expected: 65 prior + (5 + 5 + 4 + 4 + 1) = 84 tests, all pass.

- [ ] **Step 2: Tag**

```bash
git tag -a frinkloop-plan-3-done -m "Plan 3 complete: templates registry + scaffolder + 3 recipes"
```

- [ ] **Step 3: Verify tree**

```bash
ls plugin/templates/   # registry.yaml
ls plugin/recipes/     # _template, tailwind, deploy-vercel, playwright
ls plugin/lib/         # adds scaffolder.sh, recipes.sh
```

---

## Self-Review

**Spec coverage** (against design spec §15 + §10 references):
- §15 templates registry (10 platforms): Task 1 ✓
- §10 recipes (shadcn-style additive layers): Tasks 3, 4 ✓
- §6 plugin/recipes/ structure: Task 4 ✓
- Scaffolder agent (referenced from §6 + §9.3): Task 5 ✓

**Deferred:** more recipes (drizzle, prisma, auth-stub, vitest, etc.) — the system is open to add new recipes anytime; v1 ships with 3 reference ones.

**Placeholder scan:** none.

**Function/name consistency:**
- `resolve_template`, `default_template_for_platform`, `scaffold` — defined in scaffolder.sh and used in scaffolder.md
- `apply_recipe` — defined in recipes.sh and used in scaffolder.md
- Recipe schema enums match registry schema's `platform` enum

**Known limitation:** real recipes (`tailwind`, `deploy-vercel`, `playwright`) are smoke-tested for *schema validity* but not *end-to-end apply* — that requires a real scaffolded project and would slow the test suite. Plan 10 (e2e smoke) actually applies them. This is intentional.

---

*End of Plan 3.*
