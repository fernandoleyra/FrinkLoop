#!/usr/bin/env bash
# FrinkLoop caveman compression helper.
# Provides caveman_prefix() — prepends a telegraphic compression directive to
# subagent prompts when config.yaml has compression: lite | full | ultra.
# Caller sources this file and calls caveman_prefix "$compression_level" "$prompt".

set -euo pipefail

# caveman_prefix <level> <prompt>
# Prints the prompt with a compression preamble prepended.
# level: lite | full | ultra | none | ""
# Returns the prompt unchanged if level is "none" or empty.
caveman_prefix() {
  local level="${1:-none}"
  local prompt="$2"

  case "$level" in
    none|"")
      printf '%s' "$prompt"
      ;;
    lite)
      printf '%s\n\n%s' \
        "COMPRESS: respond in terse prose. No filler. Short sentences." \
        "$prompt"
      ;;
    full)
      printf '%s\n\n%s' \
        "CAVEMAN MODE: speak like caveman. short words. no fluff. grunt-level terse. get job done." \
        "$prompt"
      ;;
    ultra)
      printf '%s\n\n%s' \
        "ULTRA CAVEMAN: 1-3 word answers only. abbreviate everything. no punctuation beyond period. act not explain." \
        "$prompt"
      ;;
    *)
      printf '%s' "$prompt"
      ;;
  esac
}

# read_compression_level [config_yaml_path]
# Reads the compression level from config.yaml. Returns "none" if unset.
read_compression_level() {
  local config_path="${1:-${FRINKLOOP_DIR:-}/config.yaml}"
  if [ ! -f "$config_path" ]; then
    echo "none"
    return 0
  fi
  local level
  level=$(yq -r '.compression // "none"' "$config_path" 2>/dev/null || echo "none")
  echo "${level:-none}"
}
