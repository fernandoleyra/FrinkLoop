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
