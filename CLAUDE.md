# FrinkLoop

Source for the **FrinkLoop Claude Code plugin** — autonomous MVP development inside Claude Code.

## How it works (architecture in one paragraph)

FrinkLoop is a Claude Code plugin. Once installed, it lives at `~/.claude/plugins/frinkloop/`. Users invoke it from any project directory via slash commands (e.g. `/frinkloop new`). When FrinkLoop runs against a project, it creates a `.frinkloop/` directory **inside that project** to hold local state (config, spec, iteration logs). **This repo never holds user projects** — it holds the plugin source itself.

## Repo layout

| Path | Purpose |
|------|---------|
| `plugin/` | The plugin payload — skills, commands, hooks, lib, templates, recipes. This directory is what `claude plugin install` ships. |
| `tests/` | `bats` tests organized by plan number (`tests/plan-N/`). |
| `docs/superpowers/specs/` | Design specs. |
| `docs/superpowers/plans/` | Per-plan implementation plans + roadmap. |
| `package.json` | Dev tooling — `bats` runner, `ajv-cli` for JSON schema validation. |
| `.worktrees/` | Local git worktrees for parallel plan branches (gitignored). |

## Develop and test

```bash
npm install              # bats + ajv-cli
npm test                 # runs bats tests/
bats tests/plan-1/       # run a subset
```

## Design docs

- Spec: `docs/superpowers/specs/2026-04-30-frinkloop-plugin-redesign-design.md`
- Roadmap: `docs/superpowers/plans/2026-04-30-frinkloop-roadmap.md`
- Per-plan tasks: `docs/superpowers/plans/2026-04-30-plan-N-*.md`

## End-user docs

See [`plugin/README.md`](plugin/README.md) for install + commands.

## License

MIT
