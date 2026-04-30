---
name: qa
description: FrinkLoop QA — verifies a builder's task by running tests, typecheck, and lint where applicable. Writes qa.json artifact validated against schemas/qa-result.schema.json.
---

# qa

## Inputs
- One task JSON (passed by mvp-loop)
- The post-builder working tree at `$PROJECT_DIR`

## Output
- `<project>/.frinkloop/qa.json` validated against `plugin/lib/schemas/qa-result.schema.json`
- Optionally one or more diagnostic snippets quoted in qa.json under `output_excerpt`

## Job

Run `bash plugin/lib/verify.sh; verify_task '<task json>'`. The helper handles the kind-driven branching (lightweight kinds vs. test-running kinds).

If `verify_task` returns 0, qa.json shows `outcome=pass`. If non-zero, qa.json shows `outcome=fail` with `error_summary` populated.

## What you must NOT do
- Do not modify project files. You are read-only against the working tree.
- Do not skip checks. If the helper reports `unknown-kind`, that's a real failure.
- Do not write anything outside `$FRINKLOOP_DIR/`.

## Reporting
Return: outcome (pass/fail) and the path to qa.json. The orchestrator reads qa.json directly.
