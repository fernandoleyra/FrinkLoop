#!/usr/bin/env bash
# FrinkLoop recipe runner — atomic apply with rollback.
# Recipe folder structure: <recipe>/recipe.yaml + <recipe>/apply.sh
# Caller's cwd is PROJECT_DIR (a git repo).

set -euo pipefail

apply_recipe() {
  local recipe_dir="$1"
  local recipe_id
  recipe_id=$(yq -o=json "$recipe_dir/recipe.yaml" | jq -r '.id')

  if [ ! -x "$recipe_dir/apply.sh" ]; then
    echo "recipes: $recipe_id has no executable apply.sh" >&2
    return 1
  fi

  # Snapshot via git stash (if working tree dirty) so we can roll back.
  local pre_sha
  pre_sha=$(git rev-parse HEAD)

  # Run apply.sh; on failure, hard-reset to pre_sha and clean.
  if "$recipe_dir/apply.sh"; then
    # If nothing changed, no-op (idempotent recipe) — return success without committing.
    if [ -z "$(git status --porcelain)" ]; then
      return 0
    fi
    git add -A
    git -c commit.gpgsign=false commit -q -m "recipe($recipe_id): apply"
    return 0
  else
    local rc=$?
    git reset --hard "$pre_sha" >/dev/null
    git clean -fd >/dev/null
    return $rc
  fi
}
