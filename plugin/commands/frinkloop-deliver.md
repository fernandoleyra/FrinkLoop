---
description: Run the deliverable packaging step — README, landing copy, screenshots, and deploy for a finished FrinkLoop project.
---

# /frinkloop deliver <project>

Packages a completed FrinkLoop project into shareable deliverables: documentation, screenshots, and a Vercel deploy.

## Steps

1. Resolve `<project>` to an absolute path. Export `PROJECT_DIR` and `FRINKLOOP_DIR=<project>/.frinkloop`.
2. Validate that `state.json` has `status=done`. If not, abort: "Project is not done — run mvp-loop first."
3. Dispatch the `doc-writer` subagent to produce `README.md`, `docs/LANDING.md`, and `docs/API.md` (if applicable).
4. Dispatch the `screenshot-capturer` subagent:
   - Start the dev server: `npm run dev &` and wait for it to respond on `$PORT` (default 5173).
   - Run captures. Kill dev server on completion.
   - If Playwright is missing, apply the `playwright` recipe first.
5. Optionally deploy to Vercel:
   - Check `config.yaml` for `deploy: vercel`. If set, apply the `deploy-vercel` recipe.
   - On success, print the deploy URL.
6. Print a summary:
   ```
   Deliverables ready for <project>:
   - README:      <project>/README.md
   - Landing:     <project>/docs/LANDING.md
   - Screenshots: <project>/docs/screenshots/ (hero, feature-1, mobile)
   - Deploy:      <vercel-url or "skipped">
   ```

## Subagents dispatched

- `doc-writer` — README, landing, API docs
- `screenshot-capturer` — Playwright PNG captures

## Config keys read from `config.yaml`

| Key | Default | Meaning |
|-----|---------|---------|
| `deploy` | `none` | `vercel` to auto-deploy |
| `screenshot_url` | `http://localhost:5173` | Base URL for screenshots |
