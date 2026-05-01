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
