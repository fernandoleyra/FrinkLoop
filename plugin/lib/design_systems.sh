#!/usr/bin/env bash
# FrinkLoop design system helpers.
# DS_ROOT defaults to ~/.claude/plugins/frinkloop/design-systems
# but can be overridden by the caller (used in tests).

set -euo pipefail

: "${DS_ROOT:=$HOME/.claude/plugins/frinkloop/design-systems}"

ds_list() {
  if [ ! -d "$DS_ROOT" ]; then return 0; fi
  ls -1 "$DS_ROOT" 2>/dev/null | while read -r name; do
    [ -d "$DS_ROOT/$name" ] && echo "$name"
  done
}

ds_get() {
  local name="$1"
  local path="$DS_ROOT/$name"
  if [ ! -d "$path" ]; then return 1; fi
  echo "$path"
}

# Scaffold a new DS by copying claude-default's structure.
# Updates tokens.json's name field to the new name.
ds_create() {
  local name="$1"
  local description="${2:-}"
  local target="$DS_ROOT/$name"
  if [ -d "$target" ]; then
    echo "ds: $name already exists" >&2
    return 1
  fi
  local source_default
  source_default="$(dirname "${BASH_SOURCE[0]}")/../design-systems/claude-default"
  cp -R "$source_default" "$target"
  local tmp
  tmp=$(mktemp)
  jq --arg n "$name" --arg d "$description" '
    .name = $n
    | (if $d != "" then .description = $d else . end)
  ' "$target/tokens.json" > "$tmp"
  mv "$tmp" "$target/tokens.json"
  echo "$target"
}

# Record a source URL and scaffold a folder. Real fetch-and-extract is Plan 9 polish.
ds_clone() {
  local url="$1"
  local name="$2"
  local target="$DS_ROOT/$name"
  if [ -d "$target" ]; then
    echo "ds: $name already exists" >&2
    return 1
  fi
  ds_create "$name" "Cloned from $url" >/dev/null
  echo "$url" > "$target/clone-source.txt"
  echo "$target"
}

# Push a DS folder to a new GitHub repo. Requires gh CLI logged in.
# This is invoked manually by /frinkloop ds push, not in tests.
ds_push_github() {
  local name="$1"
  local repo="${2:-frinkloop-ds-$name}"
  local target
  target=$(ds_get "$name") || { echo "ds_push_github: $name not found" >&2; return 1; }
  (
    cd "$target"
    if [ ! -d .git ]; then
      git init -q
      git add .
      git -c commit.gpgsign=false commit -q -m "init: $name design system"
    fi
    gh repo create "$repo" --public --source=. --push 2>&1
  )
}
