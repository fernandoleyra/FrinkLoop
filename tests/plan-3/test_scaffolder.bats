#!/usr/bin/env bats

setup() {
  TMPDIR=$(mktemp -d)
  PLUGIN_LIB_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin/lib" && pwd)"
  PLUGIN_DIR="$(cd "$BATS_TEST_DIRNAME/../../plugin" && pwd)"
  source "$PLUGIN_LIB_DIR/scaffolder.sh"
  export FAKE_GIGET="$TMPDIR/fake-giget"
  cat > "$FAKE_GIGET" <<'EOF'
#!/usr/bin/env bash
# fake giget: writes args to $TMPDIR/giget.log and creates a fake project
echo "$@" > "$TMPDIR/giget.log"
target="${@: -1}"
mkdir -p "$target"
echo "scaffolded by fake giget" > "$target/README.md"
EOF
  chmod +x "$FAKE_GIGET"
  export GIGET_BIN="$FAKE_GIGET"
  export REGISTRY_FILE="$PLUGIN_DIR/templates/registry.yaml"
}

teardown() {
  rm -rf "$TMPDIR"
}

@test "resolve_template returns giget source for known id" {
  run resolve_template "vite-shadcn"
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}

@test "resolve_template returns nonzero for unknown id" {
  run resolve_template "nonexistent-template"
  [ "$status" -ne 0 ]
}

@test "default_template_for_platform returns the default for that platform" {
  run default_template_for_platform "spa-static"
  [ "$status" -eq 0 ]
  [ "$output" = "vite-shadcn" ]
}

@test "scaffold invokes giget with the right source and target" {
  scaffold "vite-shadcn" "$TMPDIR/proj"
  [ -d "$TMPDIR/proj" ]
  [ -f "$TMPDIR/proj/README.md" ]
  grep -q "vite-template" "$TMPDIR/giget.log"
}

@test "scaffold fails on unknown template" {
  run scaffold "nonexistent" "$TMPDIR/proj"
  [ "$status" -ne 0 ]
}
