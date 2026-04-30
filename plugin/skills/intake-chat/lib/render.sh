#!/usr/bin/env bash
# Renders intake-chat answer JSON into spec.md and config.yaml in $FRINKLOOP_DIR.
# Usage: render.sh <answers.json> <output_dir>

set -euo pipefail

ANSWERS="${1:?answers.json path required}"
OUTDIR="${2:?output dir required}"

mkdir -p "$OUTDIR"

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPL_DIR="$SKILL_DIR/templates"

# Delegate rendering to Python to handle multi-line substitutions correctly.
# (awk -v cannot carry literal newlines; sed is line-oriented.)
python3 - "$ANSWERS" "$TMPL_DIR" "$OUTDIR" <<'PYEOF'
import json, sys, pathlib
from datetime import datetime, timezone

answers_path, tmpl_dir, out_dir = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])

with open(answers_path) as f:
    a = json.load(f)

def list_to_bullets(items, prefix="- "):
    return "\n".join(prefix + i for i in items)

project          = a["project"]
pitch_does       = a["pitch_does"]
pitch_for        = a["pitch_for"]
pitch_proves     = a["pitch_proves"]
pitch_makes      = a["pitch_makes_them_say"]
mode             = a["mode"]
hitl             = a["hitl"]
platform         = a["platform"]
template         = a["template"]
design_system    = a["design_system"]
deploy_target    = a["deploy_target"]
compression      = a["compression"]
tdd              = str(a["tdd"]).lower()
date_val         = datetime.now(timezone.utc).strftime("%Y-%m-%d")

default_done = [
    "MVP visibly demonstrates the pitch.",
    "Core flow completes end-to-end without errors.",
    "Deploys successfully to the chosen target.",
]
default_in_mvp = [
    "Core flow described in the pitch.",
    "Minimal styling using the chosen design system.",
    "README + landing page on deliver.",
]

done_criteria   = list_to_bullets(a.get("done_criteria", default_done), "- [ ] ")
in_mvp          = list_to_bullets(a.get("in_mvp", default_in_mvp))
phase_2         = list_to_bullets(a.get("exclusions", []))
exclusions_yaml = "\n".join("  - " + e for e in a.get("exclusions", []))

spec_vars = {
    "{{PROJECT}}":             project,
    "{{PITCH_DOES}}":          pitch_does,
    "{{PITCH_FOR}}":           pitch_for,
    "{{PITCH_PROVES}}":        pitch_proves,
    "{{PITCH_MAKES_THEM_SAY}}": pitch_makes,
    "{{MODE}}":                mode,
    "{{HITL}}":                hitl,
    "{{PLATFORM}}":            platform,
    "{{TEMPLATE}}":            template,
    "{{DESIGN_SYSTEM}}":       design_system,
    "{{DEPLOY_TARGET}}":       deploy_target,
    "{{COMPRESSION}}":         compression,
    "{{TDD}}":                 tdd,
    "{{DATE}}":                date_val,
    "{{DONE_CRITERIA}}":       done_criteria,
    "{{IN_MVP}}":              in_mvp,
    "{{PHASE_2}}":             phase_2,
}

cfg_vars = {
    "{{PROJECT}}":        project,
    "{{MODE}}":           mode,
    "{{HITL}}":           hitl,
    "{{COMPRESSION}}":    compression,
    "{{PLATFORM}}":       platform,
    "{{TEMPLATE}}":       template,
    "{{DESIGN_SYSTEM}}":  design_system,
    "{{DEPLOY_TARGET}}":  deploy_target,
    "{{TDD}}":            tdd,
    "{{EXCLUSIONS_YAML}}": exclusions_yaml,
}

def render(tmpl_path, variables):
    text = tmpl_path.read_text()
    for placeholder, value in variables.items():
        text = text.replace(placeholder, value)
    return text

spec_text = render(tmpl_dir / "spec.md.tmpl", spec_vars)
cfg_text  = render(tmpl_dir / "config.yaml.tmpl", cfg_vars)

(out_dir / "spec.md").write_text(spec_text)
(out_dir / "config.yaml").write_text(cfg_text)
PYEOF

echo "Rendered: $OUTDIR/spec.md and $OUTDIR/config.yaml"
