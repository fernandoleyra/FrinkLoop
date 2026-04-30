# FrinkLoop — Plugin Redesign Design Spec

**Date:** 2026-04-30
**Author:** Fernando Leyra (with Claude Code as co-designer)
**Status:** Draft for review
**Replaces:** existing Python-based FrinkLoop framework (commit `8dde005 v3`, 2026-04-06)

---

## 1. Summary

FrinkLoop is a Claude Code **plugin** that runs autonomous MVP development from a single intake conversation to a deploy-ready, packaged deliverable. It replaces the existing Python framework entirely.

The system is designed for **AI-agent efficiency** (not human readability): token-friendly state on disk, parallel subagent fan-out, fresh-context loop iterations, and integrated compression via the `caveman` plugin. It learns locally over time (per-user, cross-project) and survives Claude Code 5-hour usage-limit interruptions via a `launchd`/`cron` wake mechanism.

The "done" output is three artifacts: a production-grade README, a deploy-ready MVP, and a Phase-2 plan describing what's deliberately out-of-MVP and what comes next.

## 2. Goals

1. One installation. Unlimited projects.
2. Autonomous from intake to delivery — no HITL needed unless user opts in.
3. Survive Claude Code usage-limit windows (5h reset) with zero user intervention.
4. Produce three concrete deliverables every run: README, deploy-ready MVP, Phase-2 plan.
5. Token-efficient by construction (caveman, fresh-context loop, ≤3KB read budget per iteration).
6. Composable: any web/API/CLI/mobile/extension/bot platform via a template registry.
7. Reusable design systems with optional remote storage in a user's GitHub.
8. Non-destructive learning: improves recommendations over time, all local, no telemetry.

## 3. Non-goals

- Auth, payments, real user data, production observability, custom infra — all explicitly **Phase 2** by default.
- Multi-project parallel runs (v2).
- Mobile-app-store delivery (v2; v1 stops at Expo dev build).
- Code review of *existing* large codebases — Ralph's known weakness, inherited.
- Telemetry, error reporting, analytics — none, ever.

## 4. Inspirations & attribution

- **Ralph Loop** (Geoffrey Huntley) — the disk-state Stop-hook loop primitive
- **caveman** (Julius Brussee) — output token compression
- **superpowers** (Jesse Vincent / Anthropic) — TDD, verification-before-completion, brainstorming, subagent patterns
- **Y Combinator** — pitch frameworks for intake structure, README, and landing-page communication

These are credited in the plugin's own README and required as a generated `## Acknowledgements` section in every MVP's README.

## 5. Architecture overview

Hybrid loop: **Stop-hook spine + parallel subagent fan-out**.

- The loop runs in a single Claude Code session. A Stop hook re-feeds `PROMPT.md` until a `DONE` token appears or `max_iterations` is hit.
- Each iteration reads ≤3 small files from disk, picks one task or one parallel batch, and writes structured artifacts back to disk.
- Independent tasks fan out via the `Task` tool (cap: 10 parallel subagents per Claude Code limit), isolated in git worktrees.
- An aggregator step reads only artifacts (never transcripts) to keep orchestrator context lean.
- All state lives on disk in machine-readable formats. Humans get a generated `STATUS.md` view if they want one.

## 6. Plugin structure

Installed at `~/.claude/plugins/<source>/frinkloop/<version>/`:

```
frinkloop/
├── plugin.json
├── commands/
│   ├── frinkloop.md             # /frinkloop      — router/help
│   ├── frinkloop-new.md         # /frinkloop new
│   ├── frinkloop-resume.md      # /frinkloop resume <project>
│   ├── frinkloop-status.md      # /frinkloop status [<project>]
│   ├── frinkloop-pause.md       # /frinkloop pause <project>
│   ├── frinkloop-ds.md          # /frinkloop ds   — design-system manager
│   └── frinkloop-deliver.md     # /frinkloop deliver <project>
├── skills/
│   ├── intake-chat/             # the clarifier conversation
│   ├── mvp-loop/                # the Stop-hook driven build loop
│   └── design-system-builder/   # DS authoring & cloning
├── agents/                      # planner, scaffolder, builder, qa, doc-writer, screenshot-capturer
├── hooks/
│   ├── stop.sh                  # re-feeds the loop on session end
│   └── post-iteration.sh        # writes JSONL log entry
├── templates/
│   └── registry.yaml            # 10-platform giget map
├── recipes/                     # shadcn-style additive layers (auth-stub, db-drizzle, deploy-vercel, …)
├── design-systems/
│   └── claude-default/          # built-in preset (Anthropic-aesthetic-ish)
├── scripts/
│   ├── quota-resume-install.sh
│   └── quota-resume.plist       # launchd template (cron fallback for Linux)
└── lib/                         # shared shell/python helpers
```

Per-project state lives **inside the project**, not in the plugin:

```
<project-dir>/
└── .frinkloop/
    ├── config.yaml              # mode, HITL, compression, design_system, deploy_target
    ├── spec.md                  # YC-shaped: Does / For / MVP proves / Done / In-MVP / Phase-2
    ├── state.json               # current pointer: milestone, task, iteration, branch, last_verified_sha
    ├── tasks.json               # milestones[] with tasks[]
    ├── decisions.md             # append-only, prose
    ├── blockers.md              # append-only, only in flag-on-blocker mode
    ├── iteration-log.jsonl      # one line per iteration: ts, iter, task_id, action, result, sha, tokens
    ├── PROMPT.md                # invariant Ralph-style loop prompt
    └── STATUS.md                # optional human-readable view, regenerated from state.json + tasks.json on demand
```

Project state in-project (not in plugin) means projects are independent, fully resumable from a fresh clone, and can be `git push`-ed including loop state.

## 7. Slash command surface

| Command | Purpose |
|---------|---------|
| `/frinkloop` | Router/help; lists active projects, recent runs, plugin version |
| `/frinkloop new` | Starts intake chat, scaffolds project, hands off to mvp-loop |
| `/frinkloop resume <project>` | Resumes a paused or quota-stopped loop |
| `/frinkloop status [<project>]` | Snapshot of state.json + last 5 iteration-log lines |
| `/frinkloop pause <project>` | Flushes state, writes handoff, exits cleanly |
| `/frinkloop ds` | Design-system manager: list / clone / create / link to remote |
| `/frinkloop deliver <project>` | Runs the deliverable packaging step |

Auto-handoff fires on: pause, blocker escalation, quota stop, and final deliver. Uses the user's existing `/handoff` skill (writes to project Handoffs, `~/.claude/handoffs`, Obsidian vault, and Notion for opted-in projects).

## 8. Intake chat flow

Driven by the `intake-chat` skill, invoked from `/frinkloop new`. **Compression OFF** during intake (user-facing prose).

YC-shaped 9-step conversation:

1. **YC pitch (4 questions)** — *Does what?* / *For whom?* / *What's the smallest version that proves it works?* / *What would make a user say "I want this"?* The 4th becomes the seed for done-criteria.
2. **Mode** — Hackathon demo / Commercial MVP / Internal demo. Affects polish bar; informs default exclusions and TDD enforcement.
3. **HITL level** — Fully autonomous / Milestone checkpoints / Flag-on-blocker only.
4. **Platform & deploy target** — auto-suggested from the pitch, user confirms or overrides. Maps to one row in `templates/registry.yaml` and sets `deploy_target` in `config.yaml` (Vercel for web fullstack/SPA/landing, manual-package for CLIs, Expo dev build for mobile, Cloudflare Workers for APIs as a non-default option, etc.).
5. **Stack preference** — user-picks-recipe vs system-picks-default-for-platform.
6. **Design system** — pick from local store / clone URL or brand / create new (via `design-system-builder`) / use stack default. Captured as `design_system: <name-or-github-ref>`.
7. **Hard exclusions confirm** — system states default exclusions (auth, payments, real user data, production observability, custom infra). User can add. With explicit warning, can remove.
8. **System proposes the spec** — folds in 2–3 model-generated recommendations and 2–3 risks. User edits inline.
9. **Final approve** — system writes `spec.md` and `config.yaml`, calls `giget` to scaffold, applies recipes, pulls design system, generates `tasks.json` and `PROMPT.md`, installs the quota-resume launchd job, hands off to `mvp-loop`.

`profile.json` (see §11) pre-fills defaults to make the conversation shorter on repeat use.

## 9. Build loop

### 9.1 Algorithm

```
1. Stop hook fires after each iteration.
2. Loop reads state.json, tasks.json (active task only), spec.md (cached).
3. Loop picks ONE task, or one parallel batch of independent tasks.
4. Independent batch → fan out via Task tool (cap 10), worktree-isolated.
   Sequential → execute inline.
5. Each subagent writes its artifact to a known output path (NOT chat).
6. Aggregator reads artifacts only, updates tasks.json + decisions.md, appends iteration-log.jsonl.
7. Run verification gate (§9.4).
8. Verification fail → enqueue fix_task with the failure output.
9. Milestone done → branch merge + checkpoint (HITL=milestones pauses here).
10. "DONE" condition met → trigger /frinkloop deliver.
11. Otherwise → Stop hook re-fires step 2.
```

Per-iteration disk-read budget target: **<3KB**.

### 9.2 State files

| File | Format | Purpose |
|---|---|---|
| `config.yaml` | YAML | mode, HITL, compression, design_system, deploy_target |
| `spec.md` | Markdown | YC-shaped frozen spec (Does / For / MVP proves / Done / In-MVP / Phase-2) |
| `state.json` | JSON | current_milestone, current_task, iteration_count, branch, last_verified_sha |
| `tasks.json` | JSON | milestones[].tasks[] with statuses |
| `decisions.md` | Markdown | append-only prose |
| `blockers.md` | Markdown | append-only; only in flag-on-blocker HITL mode |
| `iteration-log.jsonl` | JSONL | append-only; one line per iter: ts, iter, task_id, action, result, sha, tokens |
| `PROMPT.md` | Markdown | invariant loop prompt |

### 9.3 Subagent roles

Six purpose-built (`agents/`):

- **planner** — turns spec changes into task deltas
- **scaffolder** — runs `giget` + applies recipes; one-shot
- **builder** — implements one task (default workhorse, runs in worktree)
- **qa** — runs tests / typecheck / lint; writes `qa.json` artifact
- **doc-writer** — README, JSDoc, in-code comments
- **screenshot-capturer** — Playwright-driven landing + key-screen captures

Plus two reused stock subagents from the user's existing kit: **`code-reviewer`** (after each milestone) and **`bug-debugger`** (when verification fails ≥2x on the same task).

### 9.4 Verification gate

Uses `superpowers:verification-before-completion` discipline.

- **Per task:** affected files typecheck + relevant unit tests + lint
- **Per milestone:** full typecheck + full test suite + build + (if deploy_target set) preview deploy ping
- **Final ("DONE"):** all of above + deploy succeeded + screenshots captured + README links resolve

Failures don't escalate immediately. They enqueue a `fix_task` with the exact output. After 3 retries on the same fix, the issue becomes a blocker.

### 9.5 TDD discipline

- **Commercial MVP mode:** TDD on. Uses `superpowers:test-driven-development`. Every feature task spawns a paired test task that runs first; test must fail, then implementation, then test must pass.
- **Hackathon mode:** TDD off by default (speed > guarantees). User can override.
- **Internal demo mode:** TDD off by default; user can override.

### 9.6 Branching & user-conflict handling

- One branch per milestone: `frinkloop/m<N>-<slug>`. Tasks commit incrementally with conventional-commit messages.
- Milestone done → merge to main, tag `frinkloop/m<N>-done`, write checkpoint.
- **Crash recovery:** on resume, loop reads the last `iteration-log.jsonl` line and checks `git status`. Clean → resume. Dirty → user touched files; loop pauses, writes handoff, asks user via `blockers.md` to resolve.
- **Recipe atomicity:** each recipe runs `git stash` snapshot → apply → verify → commit OR rollback.

### 9.7 Token compression

- `caveman` plugin declared as peer dependency. Auto-prompts install if absent.
- Default level for loop: `full` (≈75% output token cut, accuracy preserved).
- Per-project override via `config.yaml`: `compression: lite | full | ultra`.
- Intake chat runs with compression **off**. Loop iterations + subagent prompts run with compression **on**.

## 10. Design system store & flow

Lives at `~/.claude/plugins/frinkloop/design-systems/<name>/`:

```
<ds-name>/
├── tokens.json          # color, spacing, typography, radii, shadows
├── components.md        # component-naming + behavior conventions
├── screenshots/         # reference visuals
├── source-clone/        # if cloned from a URL/brand
└── README.md            # human-facing
```

**4 ways to populate during intake step 6:**

1. Pick existing local DS by name
2. Clone from URL or brand — the `design-system-builder` skill fetches the site, extracts tokens via headless browser + Tailwind-config inference, stores
3. Create new from guided prompts (palette / type / spacing / vibe)
4. Use stack default (Tailwind + shadcn defaults)

After creation, the plugin offers: *"Want me to `git init` this and push to a new GitHub repo so it's reusable across machines?"* If yes, becomes a remote URL; projects can reference as `design_system: github:user/my-ds` in their `config.yaml`. Fetched via `giget` at scaffold time.

A built-in preset `claude-default` ships with the plugin (Anthropic / Claude.ai-aesthetic-ish — tasteful, monochrome-first, generous spacing).

## 11. Local learning

Per-user, cross-project. Lives at `~/.claude/plugins/frinkloop/learning/`:

```
learning/
├── events.jsonl         # append-only, one line per significant event
├── profile.json         # rolled-up summary read by intake-chat
└── consolidate.py       # rolls events into profile after every project close
```

**Events written** (≤200B each):
- intake_choice (field, value, platform)
- recipe_result (recipe, template, outcome, iter)
- task_verified (template, task_kind, retries)
- task_done (template, task_kind, iters, tokens) — `tokens` is for **learning estimates only** (so intake can predict iteration budgets), not for any kind of cost enforcement
- project_closed (template, mode, hitl, total_iters, total_tokens, succeeded)

**Profile fields** rolled up:
- preferred_stacks per platform
- preferred_hitl
- preferred_mode_distribution
- default_exclusions_added
- design_system_default
- recipe_blacklist (recipe+template combos that failed ≥3 times)
- avg_iters_per_task by kind
- estimated_completion_iters by mode

**How intake uses profile:** pre-fills defaults, suggests proven recipes, warns on blacklisted combos, estimates iteration budget at end of intake.

`cavemem` evaluated and **not used in v1** — it serves conversation memory; our learning is behavioral telemetry. Different jobs. Re-evaluate for v2.

## 12. Quota-aware resume

Hits when Claude Code is interrupted by 5-hour usage-limit window.

- Plugin install runs `scripts/quota-resume-install.sh` once → installs `~/Library/LaunchAgents/com.frinkloop.quota-resume.plist`. Disabled by default.
- On quota stop, exit handler:
  1. Writes `iteration-log.jsonl` line: `{event:"quota_stop", project, resume_path, quota_reset_estimate}`
  2. Writes `~/.claude/plugins/frinkloop/state/active-loop.json` pointing at the active project
  3. Schedules launchd job for `quota_reset_estimate + 60s` and **enables** it
  4. Triggers an auto-handoff before exit
- On wake: launchd runs `scripts/quota-resume.sh`, which spawns `claude --resume` with a one-line prompt: *"Resume FrinkLoop loop for `<project>`."*
- After successful wake, launchd job disables itself.
- **Linux fallback:** `systemd-timer` or `cron` equivalent. Detected at install time.

This is **not budget tracking** — there is no token budget tracker in v1. The mechanism only handles the 5-hour usage-window reset.

## 13. Privacy

- All state under `~/.claude/plugins/frinkloop/` and `<project>/.frinkloop/` is local-only.
- Network calls are limited to: (a) `giget` template fetches, (b) Vercel/Netlify deploys the user explicitly opted into, (c) `gh` push for design system if user opted in.
- No telemetry, no analytics, no error reporting.
- Stated explicitly in plugin README and in `/frinkloop` help output.

## 14. Deliverable packaging

`/frinkloop deliver` runs automatically when the loop's "DONE" criteria are met. User can also trigger it manually for partial deliveries.

Output lands in `<project>/deliverables/`:

```
<project>/
├── README.md                         # rewritten, production-grade
├── deliverables/
│   ├── landing/                      # marketing landing page
│   ├── screenshots/                  # Playwright captures
│   ├── phase-2-plan.md               # what's NOT in MVP and what's next
│   └── deploy/
│       ├── vercel-config-check.json
│       └── deploy-log.md             # live URL, build time, status
└── …code…
```

### 14.1 README composition

Generated from a deterministic skeleton — no creative variance. YC-shaped. Includes (in order): one-line elevator pitch, demo + landing links, hero screenshot, *What it does* (4 YC questions), *Quick start* (commands derived from package metadata), *Stack* (template + recipes), *Status — MVP* (checkmarks against done-criteria), *What's NOT in this MVP yet*, *Roadmap (phase 2)*, *Acknowledgements* (Ralph + caveman + superpowers + YC + FrinkLoop), *License* (MIT default, configurable at intake).

### 14.2 Landing page

Generated as a separate route in the same repo (`/landing` in Next.js, `landing.html` for static), using Astroship-style section blocks adapted to the project's design system.

YC landing-page rubric enforced:
- Above the fold: 1-line value prop "X for Y who do Z" + one CTA + 30-word hard limit on hero copy
- Show-before-tell: first scroll = screenshot/demo
- Concrete-over-abstract: rule-based pass flags adjective fluff and rewrites (`fast` → measured number)
- Single CTA above the fold, secondary CTAs below
- Sections: hero, "What it does" (3 feature cards from milestones), screenshots gallery, roadmap teaser, footer with attribution + GitHub

### 14.3 Screenshot pipeline

`screenshot-capturer` subagent.
- Playwright auto-installed on first deliver if missing (`npx playwright install --with-deps chromium`)
- Captures: hero (landing), each major feature view, mobile (375×812), dark mode if supported
- Deterministically named, stored in `deliverables/screenshots/`
- README references by relative path so they survive a fresh clone

### 14.4 Deploy step

- Detects `vercel.json` (or recipe-generated equivalent) and required CLIs at deliver-start
- Requires `gh` CLI logged in + Vercel CLI logged in (or equivalent for the chosen target). Pauses with handoff if missing.
- Runs `vercel --prod` (or recipe-defined deploy command), captures live URL
- Writes URL to `deliverables/deploy/deploy-log.md` and substitutes into README

Non-Vercel targets (Netlify, Cloudflare Pages, Render, Fly) are recipe-defined.

### 14.5 Phase-2 plan

Generated from:
- The "deferred" list frozen at intake
- Plus any tasks marked `defer_to_phase_2: true` during the build

Each item formatted as `### <title>` + 1-paragraph description + estimated effort + suggested approach. Phase 2 is **out of FrinkLoop's scope** by design — the plan tells the user what they (or another toolchain) need to do next: integrate Stripe, wire real auth, add Supabase, set up monitoring, etc.

### 14.6 Final handoff

After deliver completes, `/handoff` skill fires automatically and writes:
- `<project>/Handoffs/<date>-MVP-shipped.md`
- `~/.claude/handoffs/<date>-frinkloop-<project>.md`
- Obsidian vault entry with wikilink to `01_Projects/<project>`
- Notion 🚀 Projects DB entry (for opted-in projects)

## 15. Template registry (`templates/registry.yaml`)

| # | Platform | Template | giget source |
|---|---|---|---|
| 1 | Web fullstack | Next.js SaaS Starter (Vercel) | `gh:nextjs/saas-starter` |
| 2 | SPA / static | Vite + React + shadcn/ui | `gh:shadcn-ui/vite-template` |
| 3 | Marketing/landing | Astroship | `gh:surjithctly/astroship` |
| 4 | Node API | Hono + OpenAPI starter | `gh:w3cj/hono-open-api-starter` |
| 5 | Python API | FastAPI AI Production Template | `gh:wahyudesu/Fastapi-AI-Production-Template` |
| 6 | Node CLI | Citty (UnJS) | `gh:unjs/citty/playground` |
| 7 | Python CLI | uvinit (Typer + uv) | `gh:jlevy/uvinit` |
| 8 | Mobile | Expo Obytes Starter | `gh:obytes/react-native-template-obytes` |
| 9 | Browser ext | WXT-based starter | `gh:poweroutlet2/browser-extension-starter` |
| 10 | Discord bot | KevinNovak TS Template | `gh:KevinNovak/Discord-Bot-TypeScript-Template` |
| 10b | Slack bot | Slack Bolt TS starter | `gh:slack-samples/bolt-ts-starter-template` |

Recipes (additive layers, applied via `frinkloop add <recipe>`) live in `recipes/`. Initial set: `tailwind`, `drizzle`, `prisma`, `auth-stub`, `deploy-vercel`, `deploy-netlify`, `deploy-cloudflare`, `playwright`, `vitest`, `pwa`, `i18n`, `analytics-stub`. Each recipe is shadcn-style: idempotent, deterministic, no interactive prompts.

## 16. Open questions / risks

- **Claude Code Stop-hook stability** under quota-stop conditions — needs validation that the hook fires before the session terminates, or we lose the chance to schedule launchd. Mitigation: also write `quota_stop` log line eagerly on every iteration end, so worst case we catch up on next manual resume.
- **`giget` HTTP rate limits** for unauthenticated GitHub fetches — recipes ship as local clones inside the plugin to avoid this for the registry; only user-supplied template URLs hit GitHub raw.
- **Playwright install size** (≈300MB) on first deliver — installed lazily, not at plugin install.
- **Worktree disk usage** for parallel builders — capped via `git worktree prune` after each batch.
- **`launchd` permissions** on macOS Sequoia+ — the plugin will need a one-time consent prompt for background execution. Documented in install.

## 17. Out of scope (explicitly v2 or later)

- Multi-project parallel runs
- Mobile-app-store delivery (TestFlight, App Store Connect)
- Code review of large existing codebases
- Cost / token-budget tracking
- Conversation-memory layer (cavemem integration)
- Telemetry of any kind

## 18. Success criteria (for v1 ship)

1. End-to-end run on a Hackathon-mode Next.js MVP completes without HITL, produces all three deliverables, deploys to Vercel preview.
2. End-to-end run on a Commercial-MVP-mode Next.js project with HITL=milestones produces TDD-tested code with full test green.
3. Quota-stop midway through a run → automatic resume after 5h+1min on macOS, no user intervention.
4. Design system created locally → pushed to GitHub → consumed by a second new project on a different machine via `giget` reference.
5. Profile in `learning/profile.json` reflects user defaults after 3 completed projects.

---

*End of design spec. Implementation plan to follow once approved.*
