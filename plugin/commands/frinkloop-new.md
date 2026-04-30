---
description: Start a new FrinkLoop MVP — runs the intake-chat skill, then scaffolds and hands off to the build loop.
---

# /frinkloop new

Invoke the `intake-chat` skill to walk the user through the 4-question YC-shaped clarifier and downstream steps. The skill produces `<project>/.frinkloop/spec.md` and `<project>/.frinkloop/config.yaml`.

After the intake skill finishes:
1. Confirm scaffold path with the user (default: `~/Developer/<project-slug>`).
2. Hand off to the `mvp-loop` skill (Plan 2). For now (Plan 1), stop after intake and tell the user: "Spec written. Build loop arrives in Plan 2."
