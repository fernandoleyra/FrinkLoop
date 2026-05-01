#!/usr/bin/env bash
# deploy-vercel recipe — drops a minimal vercel.json.
set -euo pipefail

if [ -f vercel.json ]; then
  exit 0
fi

cat > vercel.json <<'EOF'
{
  "$schema": "https://openapi.vercel.sh/vercel.json"
}
EOF
