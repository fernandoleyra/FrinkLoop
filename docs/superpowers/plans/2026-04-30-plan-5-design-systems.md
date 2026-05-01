# FrinkLoop Plan 5 — Design System Store + Builder Skill + GitHub Push Flow

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Stand up the design system store under `~/.claude/plugins/frinkloop/design-systems/`, ship the built-in `claude-default` preset, replace the Plan 1 `design-system-builder` skill placeholder with a real body that supports listing, creating from prompts, cloning a URL/brand, and pushing to GitHub. Replace the Plan 1 `frinkloop-ds` slash command stub with a real router (`list`, `new`, `clone`, `push`).

**Architecture:** Each design system is a folder with `tokens.json`, `components.md`, `README.md`, optional `screenshots/`, optional `source-clone/` (when cloned). `lib/design_systems.sh` provides bash helpers (list/get/create/push). Cloning a URL is documented as a workflow but the heavy lifting (browser fetch + token extraction) is left as a Plan 9 polish task — for v1, `clone` records the URL and creates a starter folder with placeholder tokens that the user/loop fills in.

**Tech Stack:** Bash + jq + yq + bats. `gh` CLI for repo creation/push.

---

## File Structure

- Create: `plugin/design-systems/claude-default/{tokens.json, components.md, README.md}`
- Create: `plugin/lib/design_systems.sh`
- Create: `plugin/lib/schemas/design-system-tokens.schema.json`
- Modify: `plugin/skills/design-system-builder/SKILL.md` — real body
- Modify: `plugin/commands/frinkloop-ds.md` — real router with subcommand docs
- Create: `tests/plan-5/test_ds_store.bats`, `test_ds_helpers.bats`, `test_ds_command.bats`

---

## Task 1: Tokens schema + claude-default preset

**Files:** `plugin/lib/schemas/design-system-tokens.schema.json`, `plugin/design-systems/claude-default/{tokens.json, components.md, README.md}`, `tests/plan-5/test_ds_store.bats`

- [ ] **Step 1: Tests**

`tests/plan-5/test_ds_store.bats`:

```bash
#!/usr/bin/env bats

@test "claude-default tokens.json exists and is valid JSON" {
  [ -f plugin/design-systems/claude-default/tokens.json ]
  run jq . plugin/design-systems/claude-default/tokens.json
  [ "$status" -eq 0 ]
}

@test "claude-default tokens.json validates against schema" {
  run npx --no-install ajv validate -s plugin/lib/schemas/design-system-tokens.schema.json -d plugin/design-systems/claude-default/tokens.json --strict=false
  [ "$status" -eq 0 ]
}

@test "claude-default tokens has color, spacing, typography, radii" {
  for k in color spacing typography radii; do
    run jq -r ".$k" plugin/design-systems/claude-default/tokens.json
    [ "$output" != "null" ]
  done
}

@test "claude-default has components.md and README.md" {
  [ -f plugin/design-systems/claude-default/components.md ]
  [ -f plugin/design-systems/claude-default/README.md ]
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Schema**

`plugin/lib/schemas/design-system-tokens.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FrinkLoop design-system tokens.json",
  "type": "object",
  "required": ["schema_version", "name", "color", "spacing", "typography", "radii"],
  "additionalProperties": true,
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "name": { "type": "string", "minLength": 1 },
    "description": { "type": "string" },
    "color": {
      "type": "object",
      "required": ["fg", "bg", "accent"],
      "properties": {
        "fg": { "type": "string" },
        "bg": { "type": "string" },
        "accent": { "type": "string" },
        "muted": { "type": "string" },
        "border": { "type": "string" }
      },
      "additionalProperties": true
    },
    "spacing": { "type": "object", "additionalProperties": { "type": "string" } },
    "typography": {
      "type": "object",
      "required": ["fontFamily"],
      "properties": {
        "fontFamily": { "type": "string" },
        "weights": { "type": "array", "items": { "type": "integer" } },
        "scale": { "type": "object" }
      },
      "additionalProperties": true
    },
    "radii": { "type": "object", "additionalProperties": { "type": "string" } },
    "shadows": { "type": "object", "additionalProperties": { "type": "string" } }
  }
}
```

- [ ] **Step 4: claude-default preset**

`plugin/design-systems/claude-default/tokens.json`:

```json
{
  "schema_version": 1,
  "name": "claude-default",
  "description": "Anthropic Claude.ai-inspired aesthetic — tasteful, monochrome-leaning, generous spacing, restrained accents.",
  "color": {
    "fg": "#1a1a1a",
    "bg": "#fafaf9",
    "accent": "#cc7857",
    "muted": "#737373",
    "border": "#e5e5e5"
  },
  "spacing": {
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "40px",
    "2xl": "64px"
  },
  "typography": {
    "fontFamily": "ui-serif, Georgia, 'Iowan Old Style', Cambria, 'Times New Roman', Times, serif",
    "weights": [400, 500, 600],
    "scale": {
      "xs": "0.75rem",
      "sm": "0.875rem",
      "base": "1rem",
      "lg": "1.125rem",
      "xl": "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem"
    }
  },
  "radii": {
    "none": "0",
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "full": "9999px"
  },
  "shadows": {
    "sm": "0 1px 2px rgba(0,0,0,0.04)",
    "md": "0 4px 12px rgba(0,0,0,0.06)",
    "lg": "0 12px 32px rgba(0,0,0,0.08)"
  }
}
```

`plugin/design-systems/claude-default/components.md`:

```markdown
# claude-default — components

This design system favors:
- A serif body font for warmth.
- Monochrome surfaces with one accent color used sparingly (a single CTA per page, badges, error/success states only).
- Generous vertical spacing (`lg` and `xl`) between content blocks.
- Tight horizontal rhythm using `md`.

## Conventions

- **Buttons** — Primary uses `accent`, on hover darken 8%. Secondary is transparent with `border`.
- **Inputs** — `border` outline; on focus, swap border to `accent`. No drop shadows.
- **Cards** — `bg` with `radii.md`, `shadows.sm`. Padding `lg`.
- **Headlines** — Use `typography.scale.3xl` for hero. `2xl` for section titles. Always `weights[2]` (600).
- **Body** — `weights[0]` (400), `scale.base`, `1.6` line-height.

## Anti-patterns

- No gradients.
- No emoji in copy unless explicit.
- Avoid `lg` shadows; reserve for modals only.
- Never combine multiple accent shades; one accent, full stop.
```

`plugin/design-systems/claude-default/README.md`:

```markdown
# claude-default design system

The built-in FrinkLoop preset, inspired by Anthropic's Claude.ai aesthetic.

- **tokens.json** — color/spacing/typography/radii/shadows
- **components.md** — component naming + behavior conventions
- **screenshots/** (none for the built-in preset)

To use this DS in a project, set `design_system: claude-default` in `<project>/.frinkloop/config.yaml`.

To create your own, run `/frinkloop ds new <name>` (or clone a brand with `/frinkloop ds clone <url>`).
```

- [ ] **Step 5: Run, expect PASS** (4/4)

- [ ] **Step 6: Commit**

```bash
git add plugin/design-systems/claude-default/ plugin/lib/schemas/design-system-tokens.schema.json tests/plan-5/test_ds_store.bats
git commit -m "feat(design-systems): tokens schema + claude-default built-in preset"
```

---

## Task 2: `lib/design_systems.sh` helpers

**Files:** `plugin/lib/design_systems.sh`, `tests/plan-5/test_ds_helpers.bats`

- [ ] **Step 1: Tests**

`tests/plan-5/test_ds_helpers.bats`:

```bash
#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  source "$PLUGIN_LIB_DIR/design_systems.sh"
  export DS_ROOT="$TMPDIR/ds"
  mkdir -p "$DS_ROOT"
  cp -R "$PLUGIN_DIR/design-systems/claude-default" "$DS_ROOT/claude-default"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "ds_list returns the names of stored design systems" {
  run ds_list
  echo "$output" | grep -q "claude-default"
}

@test "ds_get returns the path to the named DS" {
  run ds_get claude-default
  [ "$status" -eq 0 ]
  [ -d "$output" ]
  [ -f "$output/tokens.json" ]
}

@test "ds_get returns nonzero for unknown DS" {
  run ds_get nonexistent
  [ "$status" -ne 0 ]
}

@test "ds_create scaffolds a new DS from the claude-default template" {
  ds_create my-brand "A custom brand"
  [ -d "$DS_ROOT/my-brand" ]
  [ -f "$DS_ROOT/my-brand/tokens.json" ]
  run jq -r '.name' "$DS_ROOT/my-brand/tokens.json"
  [ "$output" = "my-brand" ]
}

@test "ds_clone records the source URL in clone-source.txt" {
  ds_clone https://example.com/brand my-clone
  [ -d "$DS_ROOT/my-clone" ]
  [ -f "$DS_ROOT/my-clone/clone-source.txt" ]
  grep -q "example.com" "$DS_ROOT/my-clone/clone-source.txt"
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement `lib/design_systems.sh`**

```bash
#!/usr/bin/env bash
# FrinkLoop design system helpers.
# DS_ROOT defaults to ~/.claude/plugins/frinkloop/design-systems
# but can be overridden by the caller (used in tests).

set -euo pipefail

: "${DS_ROOT:=$HOME/.claude/plugins/frinkloop/design-systems}"

ds_list() {
  if [ ! -d "$DS_ROOT" ]; then return 0; fi
  ls -1 "$DS_ROOT" 2>/dev/null | while read -r name; do
    [ -d "$DS_ROOT/$name" ] && echo "$name"
  done
}

ds_get() {
  local name="$1"
  local path="$DS_ROOT/$name"
  if [ ! -d "$path" ]; then return 1; fi
  echo "$path"
}

# Scaffold a new DS by copying claude-default's structure.
# Updates tokens.json's name field to the new name.
ds_create() {
  local name="$1"
  local description="${2:-}"
  local target="$DS_ROOT/$name"
  if [ -d "$target" ]; then
    echo "ds: $name already exists" >&2
    return 1
  fi
  local source_default
  source_default="$(dirname "${BASH_SOURCE[0]}")/../design-systems/claude-default"
  cp -R "$source_default" "$target"
  local tmp
  tmp=$(mktemp)
  jq --arg n "$name" --arg d "$description" '
    .name = $n
    | (if $d != "" then .description = $d else . end)
  ' "$target/tokens.json" > "$tmp"
  mv "$tmp" "$target/tokens.json"
  echo "$target"
}

# Record a source URL and scaffold a folder. Real fetch-and-extract is Plan 9 polish.
ds_clone() {
  local url="$1"
  local name="$2"
  local target="$DS_ROOT/$name"
  if [ -d "$target" ]; then
    echo "ds: $name already exists" >&2
    return 1
  fi
  ds_create "$name" "Cloned from $url" >/dev/null
  echo "$url" > "$target/clone-source.txt"
  echo "$target"
}

# Push a DS folder to a new GitHub repo. Requires gh CLI logged in.
# This is invoked manually by /frinkloop ds push, not in tests.
ds_push_github() {
  local name="$1"
  local repo="${2:-frinkloop-ds-$name}"
  local target
  target=$(ds_get "$name") || { echo "ds_push_github: $name not found" >&2; return 1; }
  (
    cd "$target"
    if [ ! -d .git ]; then
      git init -q
      git add .
      git -c commit.gpgsign=false commit -q -m "init: $name design system"
    fi
    gh repo create "$repo" --public --source=. --push 2>&1
  )
}
```

- [ ] **Step 4: Run, expect PASS** (5/5)

- [ ] **Step 5: Commit**

```bash
git add plugin/lib/design_systems.sh tests/plan-5/test_ds_helpers.bats
git commit -m "feat(design-systems): helpers for list/get/create/clone/push"
```

---

## Task 3: Real `design-system-builder` skill + `frinkloop-ds` command + final

**Files:** Modify `plugin/skills/design-system-builder/SKILL.md`, modify `plugin/commands/frinkloop-ds.md`, create `tests/plan-5/test_ds_command.bats`

- [ ] **Step 1: Tests**

`tests/plan-5/test_ds_command.bats`:

```bash
#!/usr/bin/env bats

@test "design-system-builder SKILL.md no longer says 'arrives in Plan 5'" {
  ! grep -q "arrives in Plan 5" plugin/skills/design-system-builder/SKILL.md
}

@test "design-system-builder SKILL.md references all 4 modes" {
  for mode in "use existing" "clone" "create new" "stack default"; do
    grep -qi "$mode" plugin/skills/design-system-builder/SKILL.md
  done
}

@test "frinkloop-ds command no longer says 'arrives in Plan 5'" {
  ! grep -q "arrives in Plan 5" plugin/commands/frinkloop-ds.md
}

@test "frinkloop-ds command documents 4 subcommands" {
  for sub in list new clone push; do
    grep -q "/frinkloop ds $sub" plugin/commands/frinkloop-ds.md
  done
}
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Replace `design-system-builder/SKILL.md`**

```markdown
---
name: design-system-builder
description: Create, clone, or pick a FrinkLoop design system. Stores tokens, components, and screenshots locally at ~/.claude/plugins/frinkloop/design-systems/<name>/. Optionally pushes to GitHub for cross-machine reuse.
---

# design-system-builder

Manage design systems for FrinkLoop projects. Invoked from intake-chat step 6 OR directly via `/frinkloop ds`.

## Modes

### 1. Use existing (default offered first)

Run `bash plugin/lib/design_systems.sh; ds_list`. Show the user the available design systems plus the built-in `claude-default`. Capture the chosen name into the project's `config.yaml` as `design_system: <name>`.

### 2. Clone URL or brand

Run `ds_clone <url> <name>`. This records the source URL and scaffolds the folder. v1 does NOT fetch and parse the URL automatically — the user (or a Plan 9 follow-up) fills in `tokens.json` manually based on the brand. The `clone-source.txt` preserves the URL for later.

### 3. Create new

Walk the user through 4 prompts (one per turn):
- Palette: 3–5 hex colors with semantic roles (fg, bg, accent, muted, border)
- Type: font family + 3 weight choices
- Spacing: scale (xs/sm/md/lg/xl)
- Vibe: 1-paragraph description (warm/sharp/playful/serious/minimal)

Then run `ds_create <name> "<description>"`. Edit the resulting `tokens.json` with the captured values.

### 4. Use stack default

For projects scaffolded with Tailwind + shadcn, set `design_system: tailwind-shadcn-defaults`. No DS folder is created — the project's stack handles it.

## Push to GitHub

After a DS is created or refined, offer: "Want to git-init this and push to a new GitHub repo so other projects can `design_system: github:user/<repo>` it?" If yes, run `ds_push_github <name>`.

## Constraints

- Operate only inside `~/.claude/plugins/frinkloop/design-systems/`.
- Do not modify the built-in `claude-default` preset.
- Never push without explicit user consent.
```

- [ ] **Step 4: Replace `commands/frinkloop-ds.md`**

```markdown
---
description: FrinkLoop design system manager — list, create, clone, push.
---

# /frinkloop ds

Subcommand router for design system management. Source `plugin/lib/design_systems.sh` and dispatch:

## /frinkloop ds list

```bash
ds_list
```

Prints names of stored design systems under `~/.claude/plugins/frinkloop/design-systems/`. Always includes the built-in `claude-default`.

## /frinkloop ds new <name>

Invokes the `design-system-builder` skill in "create new" mode. Walks the user through palette/type/spacing/vibe and writes a fresh DS folder.

## /frinkloop ds clone <url> [<name>]

Records the URL as a clone source, scaffolds a folder named `<name>` (or a slug derived from URL). v1 does not auto-fetch tokens — `clone-source.txt` preserves the URL for later refinement.

## /frinkloop ds push <name> [<repo>]

Runs `ds_push_github <name> <repo>`. Requires `gh` CLI logged in. Creates a public repo and pushes the DS folder.

## Where DSes live

`~/.claude/plugins/frinkloop/design-systems/<name>/` with `tokens.json`, `components.md`, optional `screenshots/` and `clone-source.txt`.

Projects reference them as `design_system: <name>` (local) or `design_system: github:user/repo` (remote, fetched via giget at scaffold time).
```

- [ ] **Step 5: Run, expect PASS** (4/4)

- [ ] **Step 6: Final test suite**

```bash
bats tests/plan-1/ tests/plan-2/ tests/plan-3/ tests/plan-4/ tests/plan-5/
```

Expected: 96 prior + 4 + 5 + 4 = 109 tests pass.

- [ ] **Step 7: Tag + push + PR**

```bash
git add plugin/skills/design-system-builder/SKILL.md plugin/commands/frinkloop-ds.md tests/plan-5/test_ds_command.bats
git commit -m "feat(ds-skill): real design-system-builder skill + frinkloop-ds router"

git tag -a frinkloop-plan-5-done -m "Plan 5 complete: DS store + builder skill + GitHub push"

git push -u origin frinkloop/v0.5-design-systems
git push origin frinkloop-plan-5-done

gh pr create --base frinkloop/v0.4-parallel --head frinkloop/v0.5-design-systems \
  --title "Plan 5: Design system store + builder + GitHub push (stacks on Plan 4)" \
  --body "$(cat <<'EOF'
## Summary
Plan 5 of FrinkLoop. Stacks on Plan 4 (PR #3).

- Tokens schema (Draft-07) + built-in `claude-default` preset
- `lib/design_systems.sh` — list/get/create/clone/push helpers
- Real `design-system-builder` skill body (4 modes)
- Real `/frinkloop ds` command (list/new/clone/push)

13 new tests, 109 total.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-Review

- §10 design system store: tokens.json + components.md + README.md per DS — Task 1 ✓
- §10 4-way intake DS choice — Task 3 (skill body) ✓
- §10 GitHub push flow — Task 2 (helper) + Task 3 (command + skill) ✓
- claude-default preset shipped — Task 1 ✓

**Function/name consistency:** `ds_list`, `ds_get`, `ds_create`, `ds_clone`, `ds_push_github` — defined in lib and referenced in skill + command.

**Known v1 limitation:** `ds_clone` records URL but doesn't fetch+extract tokens. That's a Plan 9 polish task (browser fetch + Tailwind config inference).

---

*End of Plan 5.*
