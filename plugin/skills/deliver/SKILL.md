---
name: deliver
description: FrinkLoop deliver — one-shot post-build packaging. Dispatches doc-writer (README/landing/API docs), screenshot-capturer (hero/feature/mobile PNGs), and optional Vercel deploy. Run after mvp-loop completes.
---

# deliver

Packages a finished FrinkLoop project into shareable deliverables. Runs once; not a loop.

## Preconditions

- `state.json` must have `status=done`.
- `PROJECT_DIR` and `FRINKLOOP_DIR` are exported.
- `spec.md` and `decisions.md` are present (written by mvp-loop).

## Delivery algorithm

1. **Read config** — `yq e '.deploy' $FRINKLOOP_DIR/config.yaml` → deploy target (`vercel` | `none`). `yq e '.screenshot_url' ...` → base URL (default `http://localhost:5173`).

2. **doc-writer pass** — dispatch the `doc-writer` subagent with:
   - `PROJECT_DIR`, `FRINKLOOP_DIR`
   - Instruction: write `README.md`, `docs/LANDING.md`, optionally `docs/API.md`. Commit.

3. **screenshot pass** — dispatch the `screenshot-capturer` subagent:
   - Check Playwright is available (`npx playwright --version`). If not, apply the `playwright` recipe via `bash plugin/lib/recipes.sh; apply_recipe playwright`.
   - Start dev server: `npm run dev &`; wait for `$SCREENSHOT_BASE_URL` to respond (up to 30s).
   - Subagent captures hero, feature-1, mobile PNGs to `docs/screenshots/`. Commits.
   - Kill dev server.

4. **deploy pass** (optional) — if `deploy=vercel`:
   - Apply the `deploy-vercel` recipe if not already applied.
   - Run `npx vercel --prod --yes` from `$PROJECT_DIR`.
   - Capture the deploy URL from stdout and write it to `$FRINKLOOP_DIR/deploy-url.txt`.

5. **phase-2 plan** — write `$FRINKLOOP_DIR/phase-2.md` listing all spec items that were marked Phase-2 (grep `Phase-2` from `spec.md`).

6. **summary** — print the deliverable manifest to stdout (see `/frinkloop deliver` command for format).

## What this skill is NOT
- Not a loop — it runs once and exits.
- Not responsible for the build itself — that is `mvp-loop`.
- Not responsible for source code quality — that is `qa` and `critic`.

## Subagents dispatched
| Subagent | File | Purpose |
|----------|------|---------|
| doc-writer | `plugin/agents/doc-writer.md` | README, landing, API docs |
| screenshot-capturer | `plugin/agents/screenshot-capturer.md` | PNG captures via Playwright |
