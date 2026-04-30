---
description: FrinkLoop — autonomous MVP development. Show help and active projects.
---

# /frinkloop

Print this help text:

```
FrinkLoop — autonomous MVP development

  /frinkloop new                Start a new MVP (intake → scaffold → build → deliver)
  /frinkloop resume <project>   Resume a paused or quota-stopped loop
  /frinkloop status [<project>] Snapshot of loop state
  /frinkloop pause <project>    Flush state, write handoff, exit cleanly
  /frinkloop ds                 Design system manager
  /frinkloop deliver <project>  Run the deliverable packaging step

Privacy: local-only, no telemetry. See ~/.claude/plugins/.../frinkloop/README.md.
```

Then list any active loops by reading `~/.claude/plugins/frinkloop/state/active-loop.json` if present.
