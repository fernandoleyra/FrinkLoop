#!/usr/bin/env bats

setup() {
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
}

@test "tailwind recipe.yaml is valid" {
  yq -o=json "$PLUGIN_DIR/recipes/tailwind/recipe.yaml" > /tmp/t.json
  run bash -c "cd '$REPO_ROOT' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/recipe.schema.json' -d /tmp/t.json --strict=false"
  [ "$status" -eq 0 ]
}

@test "deploy-vercel recipe.yaml is valid" {
  yq -o=json "$PLUGIN_DIR/recipes/deploy-vercel/recipe.yaml" > /tmp/v.json
  run bash -c "cd '$REPO_ROOT' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/recipe.schema.json' -d /tmp/v.json --strict=false"
  [ "$status" -eq 0 ]
}

@test "playwright recipe.yaml is valid" {
  yq -o=json "$PLUGIN_DIR/recipes/playwright/recipe.yaml" > /tmp/p.json
  run bash -c "cd '$REPO_ROOT' && npx --no-install ajv validate -s '$PLUGIN_DIR/lib/schemas/recipe.schema.json' -d /tmp/p.json --strict=false"
  [ "$status" -eq 0 ]
}

@test "all 3 real recipes have executable apply.sh" {
  for r in tailwind deploy-vercel playwright; do
    [ -x "$PLUGIN_DIR/recipes/$r/apply.sh" ] || (echo "missing/exec $r" && false)
  done
}
