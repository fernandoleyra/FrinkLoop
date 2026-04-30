# FrinkLoop Implementation Roadmap

> Decomposes the 2026-04-30 design spec into independent plans, each producing working software on its own.

The spec covers 10+ subsystems. We ship them in dependency order. Each plan has its own bite-sized task file under `docs/superpowers/plans/`.

| # | Plan | Status | Filename |
|---|------|--------|----------|
| 1 | **Plugin foundation + intake chat** | ✅ written | `2026-04-30-plan-1-foundation-and-intake.md` |
| 2 | Build loop core (Stop-hook spine, builder, qa, verification) | pending | `2026-04-30-plan-2-build-loop.md` |
| 3 | Template registry + scaffolder + recipes | pending | `2026-04-30-plan-3-templates-and-recipes.md` |
| 4 | Parallel subagent fan-out + worktree isolation | pending | `2026-04-30-plan-4-parallel-subagents.md` |
| 5 | Design system store + builder skill + GitHub push flow | pending | `2026-04-30-plan-5-design-systems.md` |
| 6 | Local learning (events, profile, consolidate) | pending | `2026-04-30-plan-6-learning.md` |
| 7 | Quota-aware resume (launchd / cron) | pending | `2026-04-30-plan-7-quota-resume.md` |
| 8 | Deliverable packaging (README, landing, screenshots, deploy, phase-2) | pending | `2026-04-30-plan-8-deliverables.md` |
| 9 | Caveman integration + plugin polish + acknowledgements | pending | `2026-04-30-plan-9-caveman-and-polish.md` |
| 10 | End-to-end smoke test (Hackathon Vite+shadcn run) | pending | `2026-04-30-plan-10-e2e-smoke.md` |

## Dependency graph

```
Plan 1 (foundation + intake)
      │
      ▼
Plan 2 (build loop) ───────────────┐
      │                            │
      ├─→ Plan 3 (templates) ──────┤
      │                            │
      ├─→ Plan 4 (parallel) ───────┤
      │                            │
      ├─→ Plan 5 (design systems) ─┤
      │                            ▼
      ├─→ Plan 6 (learning) ──→ Plan 8 (deliverables)
      │                            │
      ├─→ Plan 7 (quota resume) ──┤
      │                            │
      ├─→ Plan 9 (caveman + polish)┤
                                   ▼
                              Plan 10 (e2e smoke)
```

## Shipping order

Plans 1 → 2 → 3 → 8 → 10 is the **minimum viable path** that gets a single project end-to-end. Plans 4, 5, 6, 7, 9 are improvements that can ship in any order after the minimum path is green.

## Test strategy across plans

- Each plan ships with its own tests (shell tests via `bats` for scripts, schema validation for JSON/YAML, end-to-end via plugin install + slash command invocation in a sandbox repo).
- Plan 10 is the integration check: install the plugin into a fresh `~/.claude/`, run `/frinkloop new` against a stubbed prompt, verify the entire pipeline produces all three deliverables for a small Vite+shadcn TODO MVP.

## Notes

- This roadmap lives next to the plans, not in the spec, so it can evolve as we learn during implementation.
- Each plan, when written, must self-contain its TDD steps, file paths, and complete code per the writing-plans skill rules.
