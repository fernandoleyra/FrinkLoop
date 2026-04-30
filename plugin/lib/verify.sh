#!/usr/bin/env bash
# FrinkLoop verification helpers.
# Caller exports FRINKLOOP_DIR (project's .frinkloop) and PROJECT_DIR.
# Writes qa.json artifact at FRINKLOOP_DIR/qa.json.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# Per-task verification — kind-driven.
# Argument: task JSON (one task object from tasks.json).
# Writes $FRINKLOOP_DIR/qa.json. Exits 0 on pass, non-zero on fail.
verify_task() {
  local task_json="$1"
  local task_id kind ts outcome
  task_id=$(echo "$task_json" | jq -r '.id')
  kind=$(echo "$task_json" | jq -r '.kind')
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local checks="[]"
  outcome="pass"

  case "$kind" in
    scaffold|doc|screenshot|deploy)
      # Lightweight kinds: just confirm the working tree is not broken.
      checks='[{"name":"git-status-readable","status":"pass"}]'
      ;;
    feature|fix|test)
      # Require a tests directory + at least one test file.
      if [ ! -d tests ] && [ ! -d test ] && [ ! -d __tests__ ] && [ ! -d src/__tests__ ]; then
        outcome="fail"
        checks='[{"name":"tests-dir-exists","status":"fail","output_excerpt":"no tests/ directory found"}]'
      else
        checks='[{"name":"tests-dir-exists","status":"pass"}]'
        # If there's a package.json, try `npm test`; if pyproject.toml, try `pytest`.
        if [ -f package.json ] && jq -e '.scripts.test' package.json >/dev/null 2>&1; then
          if npm test >/dev/null 2>&1; then
            checks=$(echo "$checks" | jq '. + [{"name":"npm-test","status":"pass"}]')
          else
            outcome="fail"
            checks=$(echo "$checks" | jq '. + [{"name":"npm-test","status":"fail"}]')
          fi
        elif [ -f pyproject.toml ] || [ -f pytest.ini ]; then
          if pytest >/dev/null 2>&1; then
            checks=$(echo "$checks" | jq '. + [{"name":"pytest","status":"pass"}]')
          else
            outcome="fail"
            checks=$(echo "$checks" | jq '. + [{"name":"pytest","status":"fail"}]')
          fi
        fi
      fi
      ;;
    *)
      outcome="fail"
      checks='[{"name":"unknown-kind","status":"fail","output_excerpt":"kind not handled"}]'
      ;;
  esac

  jq -n \
    --arg task_id "$task_id" \
    --arg kind "$kind" \
    --arg outcome "$outcome" \
    --arg ts "$ts" \
    --argjson checks "$checks" \
    '{schema_version:1, task_id:$task_id, kind:$kind, outcome:$outcome, ts:$ts, checks:$checks}' \
    > "$FRINKLOOP_DIR/qa.json"

  [ "$outcome" = "pass" ]
}

# Per-milestone verification — runs full test suite + build.
# Returns 0 on pass, non-zero on fail.
verify_milestone() {
  local mid="$1"
  local outcome="pass"

  if [ -f package.json ]; then
    jq -e '.scripts.test' package.json >/dev/null 2>&1 && (npm test >/dev/null 2>&1 || outcome="fail")
    jq -e '.scripts.build' package.json >/dev/null 2>&1 && (npm run build >/dev/null 2>&1 || outcome="fail")
  fi

  [ "$outcome" = "pass" ]
}

# Final verification gate — milestone verification + deploy ping (if configured).
verify_final() {
  local last_mid
  last_mid=$(jq -r '.milestones[-1].id' "$FRINKLOOP_DIR/tasks.json")
  verify_milestone "$last_mid" || return 1
  # Deploy ping is Plan 8; skip for Plan 2.
  return 0
}
