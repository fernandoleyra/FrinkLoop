#!/usr/bin/env bash
# FrinkLoop local-learning helpers.
# Caller must export FRINKLOOP_DIR before sourcing.

set -euo pipefail

: "${FRINKLOOP_DIR:?FRINKLOOP_DIR must be set}"

# emit_event <event_type> <project> <task_id> <task_kind> <duration_s> [template] [recipe]
emit_event() {
  local event="$1"
  local project="$2"
  local task_id="${3:-}"
  local task_kind="${4:-}"
  local duration_s="${5:-0}"
  local template="${6:-null}"
  local recipe="${7:-null}"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  local tmpl_val rec_val
  if [ "$template" = "null" ]; then
    tmpl_val="null"
  else
    tmpl_val="\"$template\""
  fi
  if [ "$recipe" = "null" ]; then
    rec_val="null"
  else
    rec_val="\"$recipe\""
  fi

  jq -cn \
    --arg ev "$event" \
    --arg ts "$ts" \
    --arg proj "$project" \
    --arg tid "$task_id" \
    --arg kind "$task_kind" \
    --argjson dur "$duration_s" \
    --argjson tmpl "$tmpl_val" \
    --argjson rec "$rec_val" \
    '{schema_version:1, event:$ev, ts:$ts, project:$proj, task_id:$tid, task_kind:$kind, duration_s:$dur, template:$tmpl, recipe:$rec}' \
    >> "$FRINKLOOP_DIR/events.jsonl"
}

# profile_init <project>  — writes profile.json if it doesn't exist
profile_init() {
  local project="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  [ -f "$path" ] && return 0
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  jq -n \
    --arg proj "$project" \
    --arg ts "$ts" \
    '{schema_version:1, project:$proj, created_at:$ts, updated_at:$ts,
      template_used:null, recipes_applied:[],
      task_stats:{total:0, done:0, failed:0, retried:0},
      qa_pass_rate:0, blockers:0, milestones_completed:0, total_duration_s:0}' \
    > "$path"
}

# profile_increment <counter>  — increments task_stats.<counter> and task_stats.total
profile_increment() {
  local counter="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg c "$counter" --arg ts "$ts" \
    '.task_stats[$c] += 1 | .task_stats.total += 1 | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_set_template <name>
profile_set_template() {
  local tpl="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg t "$tpl" --arg ts "$ts" \
    '.template_used = $t | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_add_recipe <recipe_name>
profile_add_recipe() {
  local recipe="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg r "$recipe" --arg ts "$ts" \
    '.recipes_applied += [$r] | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_set_qa_rate <float 0-1>
profile_set_qa_rate() {
  local rate="$1"
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --argjson r "$rate" --arg ts "$ts" \
    '.qa_pass_rate = $r | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_increment_blockers
profile_increment_blockers() {
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg ts "$ts" \
    '.blockers += 1 | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# profile_milestone_done
profile_milestone_done() {
  local path="$FRINKLOOP_DIR/profile.json"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local tmp
  tmp=$(mktemp)
  jq --arg ts "$ts" \
    '.milestones_completed += 1 | .updated_at = $ts' \
    "$path" > "$tmp"
  mv "$tmp" "$path"
}

# consolidate_profiles [global_dir]
# Sweeps all profile.json files found under global_dir (default: ~/.frinkloop/projects/)
# and writes a summary to the parent directory as global-profile.json.
consolidate_profiles() {
  local global_dir="${1:-$HOME/.frinkloop/projects}"
  local output
  output="$(dirname "$global_dir")/global-profile.json"
  local -a profiles=()
  while IFS= read -r -d '' f; do
    profiles+=("$f")
  done < <(find "$global_dir" -name "profile.json" -print0 2>/dev/null)

  if [ "${#profiles[@]}" -eq 0 ]; then
    jq -n '{schema_version:1, project_count:0, profiles:[], top_templates:[], top_recipes:[], avg_qa_pass_rate:0}' > "$output"
    return 0
  fi

  local merged="[]"
  for f in "${profiles[@]}"; do
    merged=$(echo "$merged" | jq --slurpfile p "$f" '. + $p')
  done

  echo "$merged" | jq \
    '{schema_version:1,
      project_count: length,
      profiles: .,
      top_templates: (map(select(.template_used != null) | .template_used) | group_by(.) | map({template:.[0], count:length}) | sort_by(-.count) | .[0:5]),
      top_recipes: (map(.recipes_applied // []) | flatten | group_by(.) | map({recipe:.[0], count:length}) | sort_by(-.count) | .[0:5]),
      avg_qa_pass_rate: (map(.qa_pass_rate) | if length > 0 then (add/length) else 0 end)
    }' > "$output"
}
