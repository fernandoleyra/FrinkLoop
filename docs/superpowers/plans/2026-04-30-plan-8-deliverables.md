# FrinkLoop Plan 8 — Deliverable Packaging

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Ship the deliverable layer — real `doc-writer` and `screenshot-capturer` agent bodies, a real `/frinkloop deliver` command, and a `deliver` skill that orchestrates all three deliverable types (README/docs, screenshots, deploy). After this plan, running `/frinkloop deliver <project>` produces a complete, shareable artifact set from any finished FrinkLoop project.

**Architecture:** `deliver` is a skill (not a loop) — it runs once after `mvp-loop` completes. It dispatches `doc-writer` to produce README + JSDoc, `screenshot-capturer` to produce hero/feature/mobile PNGs using Playwright, and a deploy subcommand to push to Vercel (via the existing deploy-vercel recipe). All subagents are read-only against the project tree except for their output paths.

**Tech Stack:** Bash + Playwright (already a recipe) for screenshots, `gh` CLI for deploy, `yq` for config.

---

## File Structure

- Modify: `plugin/agents/doc-writer.md` — real body
- Modify: `plugin/agents/screenshot-capturer.md` — real body
- Modify: `plugin/commands/frinkloop-deliver.md` — real command
- Create: `plugin/skills/deliver/SKILL.md`
- Create: `tests/plan-8/test_deliverables.bats`

---

## Task 1: Real agent bodies

**Files:** `plugin/agents/doc-writer.md`, `plugin/agents/screenshot-capturer.md`

- [ ] **Step 1: Replace `doc-writer.md`**

```markdown
---
name: doc-writer
description: FrinkLoop doc-writer — produces README.md, JSDoc comments, and a one-page landing copy block for any finished project. Dispatched by the deliver skill after mvp-loop completes.
---

# doc-writer

## Inputs
- `$PROJECT_DIR` — the project working tree (read-only except for output paths)
- `$FRINKLOOP_DIR/spec.md` — the frozen MVP spec (what was intended)
- `$FRINKLOOP_DIR/decisions.md` — architectural decisions log

## Output paths
- `$PROJECT_DIR/README.md` — full README (install, usage, screenshots placeholder, tech stack)
- `$PROJECT_DIR/docs/LANDING.md` — one-page landing copy (headline, value prop, 3 features, CTA)
- `$PROJECT_DIR/docs/API.md` — if the project exports an API, document it here

## Job

1. Read `spec.md` for the product description and MVP scope.
2. Read `decisions.md` for tech stack choices and known limitations.
3. Scan `$PROJECT_DIR/src/` (or `app/`, `lib/`) for exported functions/components.
4. Write `README.md` with sections: Description, Prerequisites, Install, Usage, Screenshots (placeholder with `![hero](docs/screenshots/hero.png)`), Tech Stack, Known Limitations.
5. Write `docs/LANDING.md` with: headline (≤10 words), value prop (≤30 words), 3 feature bullet points, CTA ("Try it:" + run command).
6. If API surface exists, write `docs/API.md` with one code example per exported function.
7. Commit: `git commit -m "docs: deliverable README + landing copy"`.

## Constraints
- Do NOT modify source code.
- Do NOT add dependencies.
- Code examples in docs must be runnable (copy-paste ready).
- Keep README under 200 lines; link to docs/ for deep content.
```

- [ ] **Step 2: Replace `screenshot-capturer.md`**

```markdown
---
name: screenshot-capturer
description: FrinkLoop screenshot-capturer — Playwright-driven PNG captures: hero (1280×800), feature (1280×800), and mobile (375×812). Writes to docs/screenshots/. Dispatched by the deliver skill.
---

# screenshot-capturer

## Preconditions
- The project must be running locally (dev server or production build served on localhost).
- Playwright must be installed (apply the `playwright` recipe if missing).
- `SCREENSHOT_BASE_URL` env var points to the running app (default: `http://localhost:5173`).

## Inputs
- `$PROJECT_DIR` — writable for output
- `SCREENSHOT_BASE_URL` — base URL of the running app

## Output paths
- `$PROJECT_DIR/docs/screenshots/hero.png` — full-viewport desktop landing
- `$PROJECT_DIR/docs/screenshots/feature-1.png` — key feature interaction
- `$PROJECT_DIR/docs/screenshots/mobile.png` — mobile viewport (375×812)

## Job

1. Check that Playwright is installed: `npx playwright --version`. If missing, instruct the loop to apply the playwright recipe first.
2. Write a minimal Playwright script at `$FRINKLOOP_DIR/capture.js`:

```js
const { chromium } = require('playwright');
const base = process.env.SCREENSHOT_BASE_URL || 'http://localhost:5173';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  // Hero
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(base);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'docs/screenshots/hero.png', fullPage: false });

  // Feature: click the first interactive element and capture
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(base);
  const btn = page.locator('button, [role="button"]').first();
  if (await btn.isVisible()) await btn.click();
  await page.screenshot({ path: 'docs/screenshots/feature-1.png' });

  // Mobile
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto(base);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'docs/screenshots/mobile.png' });

  await browser.close();
})();
```

3. `mkdir -p $PROJECT_DIR/docs/screenshots`
4. Run: `cd $PROJECT_DIR && SCREENSHOT_BASE_URL=$SCREENSHOT_BASE_URL node $FRINKLOOP_DIR/capture.js`
5. Verify all three PNGs exist and are non-empty.
6. Commit: `git commit -m "docs: add hero, feature, and mobile screenshots"`.

## Fallback
If the dev server is not running or Playwright times out, write placeholder SVG files at each path so the README links don't break, and log a warning to `$FRINKLOOP_DIR/blockers.md`.
```

- [ ] **Step 3: Tests (agent body checks)**

`tests/plan-8/test_deliverables.bats`:

```bash
#!/usr/bin/env bats

@test "doc-writer agent no longer has placeholder text" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/doc-writer.md
}

@test "doc-writer agent references spec.md and decisions.md" {
  grep -q "spec.md" plugin/agents/doc-writer.md
  grep -q "decisions.md" plugin/agents/doc-writer.md
}

@test "doc-writer agent specifies README and LANDING.md outputs" {
  grep -q "README.md" plugin/agents/doc-writer.md
  grep -q "LANDING.md" plugin/agents/doc-writer.md
}

@test "screenshot-capturer agent no longer has placeholder text" {
  ! grep -q "Placeholder. Will be implemented" plugin/agents/screenshot-capturer.md
}

@test "screenshot-capturer agent references hero and mobile screenshots" {
  grep -q "hero.png" plugin/agents/screenshot-capturer.md
  grep -q "mobile.png" plugin/agents/screenshot-capturer.md
}

@test "screenshot-capturer agent references Playwright" {
  grep -q "playwright\|Playwright" plugin/agents/screenshot-capturer.md
}

@test "frinkloop-deliver command no longer says 'arrives in Plan 8'" {
  ! grep -q "arrives in Plan 8" plugin/commands/frinkloop-deliver.md
}

@test "frinkloop-deliver command documents doc-writer and screenshot-capturer" {
  grep -q "doc-writer" plugin/commands/frinkloop-deliver.md
  grep -q "screenshot-capturer" plugin/commands/frinkloop-deliver.md
}

@test "deliver skill exists with correct frontmatter" {
  [ -f plugin/skills/deliver/SKILL.md ]
  grep -q "deliver" plugin/skills/deliver/SKILL.md
}

@test "deliver skill references all 3 deliverable types" {
  grep -q "README\|docs" plugin/skills/deliver/SKILL.md
  grep -q "screenshot" plugin/skills/deliver/SKILL.md
  grep -q "deploy\|Vercel\|vercel" plugin/skills/deliver/SKILL.md
}
```

---

*End of Plan 8.*
