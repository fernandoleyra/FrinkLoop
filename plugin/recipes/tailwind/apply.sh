#!/usr/bin/env bash
# Tailwind recipe — installs tailwind, postcss, autoprefixer; inits config.
set -euo pipefail

if [ ! -f package.json ]; then
  echo "tailwind recipe: no package.json found" >&2
  exit 1
fi

npm install -D tailwindcss@^3 postcss@^8 autoprefixer@^10 >/dev/null 2>&1

if ! [ -f tailwind.config.js ] && ! [ -f tailwind.config.ts ]; then
  npx --yes tailwindcss init -p >/dev/null 2>&1 || cat > tailwind.config.js <<'EOF'
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
EOF
fi
