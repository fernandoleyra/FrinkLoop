#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export PROJECT_DIR="$TMPDIR/demo-project"
  mkdir -p "$PROJECT_DIR/.frinkloop"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "end-to-end Plan 1 smoke: render spec + config from answers, validate, state init works" {
  cat > /tmp/answers-e2e.json <<EOF
{
  "project": "demo-project",
  "pitch_does": "A live briefing instrument for creative agencies",
  "pitch_for": "agency planners pre-meeting",
  "pitch_proves": "user can run a full 5-min briefing flow without confusion",
  "pitch_makes_them_say": "I want this in every weekly review",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel",
  "compression": "full",
  "exclusions": ["analytics", "auth", "real-user-data"],
  "tdd": false
}
EOF

  # Step 1: render the spec + config
  plugin/skills/intake-chat/lib/render.sh /tmp/answers-e2e.json "$PROJECT_DIR/.frinkloop"
  [ -f "$PROJECT_DIR/.frinkloop/spec.md" ]
  [ -f "$PROJECT_DIR/.frinkloop/config.yaml" ]

  # Step 2: validate config against schema
  yq -o=json "$PROJECT_DIR/.frinkloop/config.yaml" > /tmp/cfg-e2e.json
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/cfg-e2e.json --strict=false
  [ "$status" -eq 0 ]

  # Step 3: state_init produces a valid state.json
  export FRINKLOOP_DIR="$PROJECT_DIR/.frinkloop"
  source plugin/lib/state.sh
  state_init main
  [ -f "$FRINKLOOP_DIR/state.json" ]

  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d "$FRINKLOOP_DIR/state.json" --strict=false
  [ "$status" -eq 0 ]

  # Step 4: log_iteration writes a JSONL line
  log_iteration '{"event":"intake_done","project":"demo-project"}'
  [ -f "$FRINKLOOP_DIR/iteration-log.jsonl" ]
  run wc -l < "$FRINKLOOP_DIR/iteration-log.jsonl"
  [ "$output" -eq 1 ]
}
