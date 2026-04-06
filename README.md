# Agent OS

**A persistent, reusable autonomous development system.**
One installation. Unlimited projects. A team of AI agents that plans, builds, tests, and reviews — and only stops when your software is ready.

```
You write a BRIEF.md  →  Agents plan, research, build, test, and review  →  You get notified when done
```

---

## How it works

A team of specialized agents coordinates through a shared `memory/` folder. They never call each other directly — they communicate through files.

| Agent | Role |
|-------|------|
| **Orchestrator** | Reads your brief, creates milestones, assigns all tasks |
| **Researcher** | Investigates unknowns, picks libraries, writes findings |
| **Developer** | Writes all production code |
| **QA** | Tests everything, blocks bad code from advancing |
| **Critic** | Reviews code quality, rejects anything not production-ready |
| **Docs** | Writes README, API docs, and code comments |

The loop runs autonomously: pick task → spawn agent → QA → Critic → commit → next task.
It stops only for hard escalation conditions (repeated failures, security flags, or success).

When it stops and needs you, it asks interactively — you can add context, skip, or replace a task and the loop resumes without restarting.

---

## Install

```bash
git clone https://github.com/your-username/agent-os
cd agent-os
pip install -r requirements.txt   # Python 3.11+ required
python agentos.py init            # interactive setup (API key, GitHub, Obsidian)
```

`init` walks you through setting up `.env`. You can also copy `.env.example` and fill it manually.

---

## Quickstart

```bash
# 1. Create a project — interactive brief builder
python agentos.py new my-app

# 2. Start the build
python agentos.py run my-app

# 3. Watch it live (open a second terminal)
python agentos.py watch my-app
```

`watch` shows a live table of milestones, task status, and recent agent activity.
Press `d` for decisions, `b` for blockers, `q` to quit.

---

## Commands

```bash
python agentos.py init              # first-time setup wizard
python agentos.py new  <name>       # create a project with an interactive brief builder
python agentos.py run  <name>       # start or resume the agent loop
python agentos.py watch <name>      # live dashboard (separate terminal)
python agentos.py status [name]     # print project status
python agentos.py handoff <name>    # snapshot state for cross-device continuity
python agentos.py handoff <name> --push   # snapshot + push to GitHub
python agentos.py wake <name>       # resume from a handoff snapshot on a new machine
```

### Cross-device workflow

```bash
# On your current machine — before you leave
python agentos.py handoff my-app --push

# On the new machine
git clone <your-repo>
pip install -r requirements.txt
python agentos.py init
python agentos.py wake my-app      # reads HANDOFF.md, resets interrupted tasks, resumes
```

---

## BRIEF.md format

This is the only file you write. `agentos new` builds it interactively, or write it yourself:

```markdown
# Project Brief

## What to build
Plain English. One paragraph is enough.

## Key requirements
- Must-have feature 1
- Must-have feature 2

## Tech preferences
e.g. "TypeScript + Hono", "FastAPI + PostgreSQL" — or leave blank

## What "done" looks like
Acceptance criteria — how you'll know it works

## Out of scope
What should NOT be built in this iteration
```

---

## Project structure

```
projects/my-project/
├── BRIEF.md              ← you write this (or use agentos new)
├── HANDOFF.md            ← written by agentos handoff
├── src/                  ← all generated production code
├── tests/                ← all generated tests
└── memory/
    ├── plan.md           ← Orchestrator writes milestones
    ├── tasks.json        ← live task queue
    ├── decisions.md      ← append-only architectural decisions log (auto-compressed)
    ├── blockers.md       ← agents write here when stuck
    ├── qa_report.md      ← QA writes test results
    ├── research/         ← Researcher findings (*.md)
    └── agent_logs/       ← full output of every agent call (timestamped)
```

---

## Agent OS structure

```
agent-os/
├── agentos.py            ← CLI entry point (init, new, run, watch, handoff, wake)
├── CLAUDE.md             ← Orchestrator identity (read every session)
├── DEVOS_PLAY.md         ← alternate mode: run entirely inside Claude Code
├── requirements.txt
├── .env.example
│
├── agents/               ← agent role definitions — edit to change behavior
│   ├── orchestrator.md
│   ├── developer.md
│   ├── researcher.md
│   ├── qa.md
│   ├── critic.md
│   └── docs.md
│
├── core/                 ← the engine
│   ├── loop.py           ← main iteration loop
│   ├── spawn.py          ← builds prompts and calls Claude API
│   ├── memory.py         ← shared memory interface + decisions compression
│   ├── escalation.py     ← hard-stop conditions
│   ├── github.py         ← git commits + GitHub API integration
│   ├── handoff.py        ← cross-device handoff/wake logic
│   ├── watch.py          ← live terminal dashboard
│   ├── obsidian.py       ← Obsidian vault sync
│   ├── conventions.md    ← coding standards injected into every developer prompt
│   ├── escalation-rules.md
│   └── task-schema.md
│
├── config/
│   └── defaults.yaml     ← documents all settings
│
├── templates/            ← starter scaffolds (api, cli-tool, scraper, web-app)
├── scripts/              ← legacy shell scripts (still work)
├── memory/               ← global state (gitignored except folder structure)
└── projects/             ← all your projects live here (gitignored except _template)
    └── _template/        ← copied when creating a new project
```

---

## Integrations

### GitHub
Set `GITHUB_TOKEN` in `.env` (needs `repo` scope).

- `agentos new` can create the GitHub repo for you
- Every completed task becomes a conventional commit: `feat(T07): build auth endpoint [agent: developer]`
- Every completed milestone pushes to origin
- Blockers that hit max retries automatically open a GitHub issue

### Obsidian
Set `OBSIDIAN_VAULT_PATH` in `.env`.

After each task, four notes are written to `<vault>/DevOS/<project-name>/`:
- `Dashboard.md` — task table with progress
- `Decisions.md` — current architectural decisions
- `Blockers.md` — active blockers
- `QA Report.md` — latest test results

All notes have YAML frontmatter and `[[wiki links]]` to each other.

### Claude Code (alternate mode)
See `DEVOS_PLAY.md` — runs the full Agent OS loop inside a Claude Code session with no Python process needed.

---

## Configuration

All settings are documented in `config/defaults.yaml`. To actually change them, edit the constants in `core/loop.py`, `core/spawn.py`, or `core/escalation.py` directly.

Key settings:

| Setting | Default | Location |
|---------|---------|----------|
| Model | `claude-sonnet-4-20250514` | `core/spawn.py` |
| Max task retries before escalation | 5 | `core/loop.py` |
| Max critic rejections before escalation | 3 | `core/escalation.py` |
| Max loop iterations (hard stop) | 200 | `core/loop.py` |
| Decisions compression threshold | 4 000 chars | `core/memory.py` |

---

## Escalation

The loop pauses and asks for input when:

| Condition | Threshold |
|-----------|-----------|
| Same task fails repeatedly | `fail_count >= 5` |
| Critic rejects same task repeatedly | `critic_rejections >= 3` |
| Security vulnerability flagged | "SECURITY" or "VULNERABILITY" in blockers |
| Max iterations reached | 200 |
| All milestones complete | — (success) |

When escalation fires, you see an interactive menu:
```
  [1] Add context and retry
  [2] Skip this task
  [3] Replace with a different approach
  [4] View full error log
  [5] Stop — I'll handle it manually
```

---

## Adding a new agent

1. Create `agents/my-agent.md` (follow the pattern of existing agents)
2. Add to `AGENT_TASK_MAP` in `core/loop.py`
3. Optionally inject context in `core/spawn.py` → `_build_context()`
4. Document in `config/defaults.yaml`

---

## Contributing

Contributions welcome. A few things worth knowing:

- `agents/` and `core/` are the two surfaces where most improvements land
- The best improvements are usually to agent prompts in `agents/` — they have a big impact with zero code changes
- `core/memory.py` and `core/spawn.py` are the right places for context management improvements
- Keep sub-agents write-only to `projects/<name>/` — never to `agents/` or `core/`

If you're adding a new integration (new tool, new memory backend, new model provider), open an issue first so we can align on the interface before you build.

---

## Acknowledgments

Agent OS was shaped by ideas from across the agentic AI ecosystem. These projects were direct sources of inspiration:

**Agentic software development**
- [Aider](https://github.com/Aider-AI/aider) — repo map with tree-sitter + PageRank for selective context injection; git-as-audit-trail per task
- [OpenHands](https://github.com/OpenHands/OpenHands) — event-stream architecture as a single source of truth; sandbox isolation patterns
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) — Agent-Computer Interface (ACI) design; syntax validation before accepting edits
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT) — SOP-as-code; publish-subscribe shared message pool between agents
- [ChatDev](https://github.com/OpenBMB/ChatDev) — dual-agent instructed dialogue for iterative review cycles

**Multi-agent orchestration**
- [AutoGen](https://github.com/microsoft/autogen) — sequential chat with structured carryover between phases
- [CrewAI](https://github.com/crewaiinc/crewai) — role-playing with defined backstory; automatic context window management
- [LangGraph](https://github.com/langchain-ai/langgraph) — interrupt/resume pattern for human-in-the-loop escalation
- [AgentScope](https://github.com/agentscope-ai/agentscope) — pipeline abstractions for composable workflows

**Context engineering**
- [LangChain context engineering](https://github.com/langchain-ai/context_engineering) — always-in-context / retrievable / archived memory tier model
- [AutoCodeRover](https://github.com/AutoCodeRoverSG/auto-code-rover) — SBFL fault localization; two-phase understand-then-patch structure

**Memory**
- [Mem0](https://github.com/mem0ai/mem0) — selective fact extraction; conflict detection and resolution in memory
- [Graphiti / Zep](https://github.com/getzep/graphiti) — bi-temporal fact storage; incremental knowledge graph updates
- [Letta (MemGPT)](https://github.com/letta-ai/letta) — self-editing agent memory; virtual context paging model

---

## License

MIT
