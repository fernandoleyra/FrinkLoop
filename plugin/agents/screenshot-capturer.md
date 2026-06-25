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
