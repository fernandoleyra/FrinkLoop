# FrinkLoop

> Autonomous MVP development for Claude Code. Intake → scaffold → build → verify → deliver.

## What it does

FrinkLoop turns a 4-question intake conversation into a deploy-ready MVP with a README, a landing page, screenshots, and a Phase-2 plan — fully autonomously, surviving Claude Code 5-hour usage windows.

## Install

```bash
claude plugin marketplace add fernandoleyra/FrinkLoop
claude plugin install frinkloop
```

## Quick start

```
/frinkloop new
```

## Commands

| Command | Purpose |
|---------|---------|
| `/frinkloop` | Router/help |
| `/frinkloop new` | Start intake chat → scaffold → build |
| `/frinkloop resume <project>` | Resume a paused or quota-stopped loop |
| `/frinkloop status [<project>]` | Snapshot of loop state |
| `/frinkloop pause <project>` | Flush state, write handoff, exit cleanly |
| `/frinkloop ds` | Design system manager |
| `/frinkloop deliver <project>` | Run the deliverable packaging step |

## Status

Early development. See `docs/superpowers/specs/2026-04-30-frinkloop-plugin-redesign-design.md` for the design and `docs/superpowers/plans/2026-04-30-frinkloop-roadmap.md` for implementation status.

## Privacy

Local-only. No telemetry. No analytics. Network calls limited to: template fetches via `giget`, deploys you opt into, and `gh` push for design systems if you opt in.

## Acknowledgements

- [Ralph Loop](https://ghuntley.com/ralph) by Geoffrey Huntley — the disk-state Stop-hook loop primitive
- [caveman](https://github.com/JuliusBrussee/caveman) by Julius Brussee — token compression
- [superpowers](https://github.com/jesseduffield/superpowers) — TDD, verification, brainstorming, subagent patterns
- Y Combinator — pitch frameworks for intake structure and communication

## License

MIT
