#!/usr/bin/env bash
# FrinkLoop scaffolder — wraps giget against the templates/registry.yaml.
# Caller may set GIGET_BIN (default: "npx --yes giget") and REGISTRY_FILE.

set -euo pipefail

: "${GIGET_BIN:=npx --yes giget}"
: "${REGISTRY_FILE:=$(dirname "${BASH_SOURCE[0]}")/../templates/registry.yaml}"

resolve_template() {
  local id="$1"
  local out
  out=$(yq -o=json "$REGISTRY_FILE" | jq -r --arg id "$id" '.templates[] | select(.id == $id) | .giget' 2>/dev/null || true)
  if [ -z "$out" ] || [ "$out" = "null" ]; then
    return 1
  fi
  echo "$out"
}

default_template_for_platform() {
  local platform="$1"
  local out
  out=$(yq -o=json "$REGISTRY_FILE" | jq -r --arg p "$platform" '
    .templates[] | select(.platform == $p and .default == true) | .id
  ' | head -1)
  if [ -z "$out" ]; then
    return 1
  fi
  echo "$out"
}

scaffold() {
  local template_id="$1"
  local target="$2"
  local source
  source=$(resolve_template "$template_id") || {
    echo "scaffolder: unknown template '$template_id'" >&2
    return 1
  }
  $GIGET_BIN "$source" "$target"
}
