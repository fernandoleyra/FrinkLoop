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
