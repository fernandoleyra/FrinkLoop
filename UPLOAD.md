# Publishing FrinkLoop to the Claude Code Marketplace

## What to upload

| File / Directory | Purpose |
|---|---|
| `plugin/` | Installable plugin payload (skills, commands, agents, hooks, lib) |
| `.claude-plugin/marketplace.json` | Registry entry |
| `assets/` | Icon and banner images |
| `README.md` | User-facing documentation |
| `CHANGELOG.md` | Version history |
| `LICENSE` | MIT license (create if missing) |

Do NOT upload: `.env`, `.env.local`, `.frinkloop/`, `.git/`, `node_modules/`, `.venv/`, `tests/`, `docs/`, `CLAUDE.md`, `UPLOAD.md`.

## Marketplace submission steps

1. Ensure the repo is public on GitHub at `github.com/fernandoleyra/FrinkLoop`
2. Tag the release:
   ```bash
   git tag v1.0.0
   git push origin main --tags
   ```
3. Create a GitHub Release with CHANGELOG content as release notes
4. Submit to the Claude Code plugin registry:
   - Plugin name: `frinkloop`
   - Owner: `fernandoleyra`
   - Source: `https://github.com/fernandoleyra/FrinkLoop`

## Install command (for users)

```
/plugin marketplace add fernandoleyra/FrinkLoop
/plugin install frinkloop
```

## Version bump instructions

1. Update `version` in `plugin/.claude-plugin/plugin.json`
2. Update `version` in `.claude-plugin/marketplace.json`
3. Add entry to `CHANGELOG.md`
4. Commit and tag
