#!/usr/bin/env bats

@test "state schema validates a minimal valid example" {
  cat > /tmp/state-valid.json <<EOF
{
  "schema_version": 1,
  "current_milestone": null,
  "current_task": null,
  "iteration_count": 0,
  "branch": "main",
  "last_verified_sha": null,
  "status": "idle"
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d /tmp/state-valid.json --strict=false
  [ "$status" -eq 0 ]
}

@test "state schema rejects missing schema_version" {
  cat > /tmp/state-bad.json <<EOF
{ "iteration_count": 0 }
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/state.schema.json -d /tmp/state-bad.json --strict=false
  [ "$status" -ne 0 ]
}

@test "tasks schema validates a milestones+tasks structure" {
  cat > /tmp/tasks-valid.json <<EOF
{
  "schema_version": 1,
  "milestones": [{
    "id": "m1",
    "title": "Scaffold",
    "status": "pending",
    "tasks": [{
      "id": "T01",
      "title": "Run giget",
      "status": "pending",
      "kind": "scaffold"
    }]
  }]
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/tasks.schema.json -d /tmp/tasks-valid.json --strict=false
  [ "$status" -eq 0 ]
}

@test "config schema validates a minimal config" {
  cat > /tmp/config-valid.json <<EOF
{
  "schema_version": 1,
  "project": "demo",
  "mode": "hackathon",
  "hitl": "fully-autonomous",
  "compression": "full",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel"
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/config-valid.json --strict=false
  [ "$status" -eq 0 ]
}

@test "config schema rejects invalid mode" {
  cat > /tmp/config-bad.json <<EOF
{
  "schema_version": 1,
  "project": "demo",
  "mode": "yolo",
  "hitl": "fully-autonomous",
  "compression": "full",
  "platform": "spa-static",
  "template": "vite-shadcn",
  "design_system": "claude-default",
  "deploy_target": "vercel"
}
EOF
  run npx --no-install ajv validate -s plugin/lib/schemas/config.schema.json -d /tmp/config-bad.json --strict=false
  [ "$status" -ne 0 ]
}
