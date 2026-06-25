---
description: Start a new FrinkLoop MVP — runs the intake-chat skill, then scaffolds and hands off to the build loop.
---

# /frinkloop new

Invoke the `intake-chat` skill to walk the user through the 4-question YC-shaped clarifier and downstream steps. The skill produces `<project>/.frinkloop/spec.md` and `<project>/.frinkloop/config.yaml`.

After the intake skill finishes:
1. Confirm scaffold path with the user (default: `~/Developer/<project-slug>`).
2. Invoke the `mvp-loop` skill to begin building.
