#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  export FRINKLOOP_DIR="$TMPDIR/.frinkloop"
  mkdir -p "$FRINKLOOP_DIR"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "intake render.sh exists and is executable" {
  [ -x plugin/skills/intake-chat/lib/render.sh ]
}

@test "render.sh produces a config.yaml that validates against schema" {
  cat > /tmp/answers.json <<EOF
{
  "project": "todo-mvp",
  "pitch_does": "A focused TODO list",
  "pitch_for": "ADHD professionals",
  "pitch_proves": "users add 3 items in <30 seconds",
  "pitch_makes_them_say": "I want this on my home screen",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel",
  "compression": "full",
  "exclusions": ["analytics", "auth"],
  "tdd": false
}
EOF
  run plugin/skills/intake-chat/lib/render.sh /tmp/answers.json "$FRINKLOOP_DIR"
  [ "$status" -eq 0 ]
  [ -f "$FRINKLOOP_DIR/config.yaml" ]
  [ -f "$FRINKLOOP_DIR/spec.md" ]

  yq -o=json "$FRINKLOOP_DIR/config.yaml" > /tmp/cfg.json
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/cfg.json --strict=false
  [ "$status" -eq 0 ]
}

@test "spec.md contains all 4 YC pitch sections" {
  cat > /tmp/answers.json <<EOF
{
  "project": "todo-mvp",
  "pitch_does": "A focused TODO list",
  "pitch_for": "ADHD professionals",
  "pitch_proves": "users add 3 items in <30 seconds",
  "pitch_makes_them_say": "I want this on my home screen",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel",
  "compression": "full",
  "exclusions": ["analytics", "auth"],
  "tdd": false
}
EOF
  plugin/skills/intake-chat/lib/render.sh /tmp/answers.json "$FRINKLOOP_DIR"
  grep -q '\*\*Does:\*\*' "$FRINKLOOP_DIR/spec.md"
  grep -q '\*\*For:\*\*' "$FRINKLOOP_DIR/spec.md"
  grep -q '\*\*MVP proves:\*\*' "$FRINKLOOP_DIR/spec.md"
  grep -q 'Done looks like' "$FRINKLOOP_DIR/spec.md"
  grep -q 'In MVP' "$FRINKLOOP_DIR/spec.md"
  grep -q 'Deferred to Phase 2' "$FRINKLOOP_DIR/spec.md"
}
