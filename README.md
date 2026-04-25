# FrinkLoop

FrinkLoop is a local-first agent loop for vibecoders who want to turn a plain-English project brief into a planned, tested, review-gated codebase.

You install it once, create many projects, and let a small team of file-based agents coordinate through project memory:

```text
BRIEF.md -> plan -> build -> QA -> critic review -> commit -> next task
```

FrinkLoop is experimental. Treat it as a hackable resource, not a hosted product or a guarantee that unattended agents will always do the right thing.

## Why It Exists

Most coding-agent workflows lose context between sessions. FrinkLoop keeps project state on disk so a loop can stop, resume, hand off to another machine, or explain what happened.

The design is intentionally simple:

- Agents communicate through files, not hidden process state.
- Every project gets its own `memory/` folder.
- QA and critic gates run after code tasks.
- Escalations pause the loop instead of pretending uncertainty is success.
- Git commits preserve progress task by task.

## Features

- Interactive project brief builder
- Multi-agent roles: orchestrator, researcher, developer, QA, critic, docs
- Provider support for Anthropic, OpenRouter, Groq, Ollama, and Gemini
- Tool-calling path for file reads/writes and commands
- GitHub repo creation, commits, pushes, and blocker issues
- Obsidian sync for dashboard, decisions, blockers, and QA notes
- Cross-device handoff and wake flow
- Local test suite for the core contracts and loop behavior

## Install

Requirements:

- Python 3.11+
- Git
- At least one supported model provider or local Ollama model

```bash
git clone https://github.com/YOUR_USERNAME/FrinkLoop.git
cd FrinkLoop
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 frinkloop.py init
```

`init` writes a local `.env`. You can also copy `.env.example` and edit it manually.

## Quickstart

```bash
python3 frinkloop.py new my-app
python3 frinkloop.py run my-app
```

In another terminal:

```bash
python3 frinkloop.py watch my-app
```

The watcher shows milestone progress, task status, and recent agent activity. Press `d` for decisions, `b` for blockers, and `q` to quit.

## Commands

```bash
python3 frinkloop.py init
python3 frinkloop.py new <name>
python3 frinkloop.py run <name>
python3 frinkloop.py run <name> --dry-run
python3 frinkloop.py watch <name>
python3 frinkloop.py status [name]
python3 frinkloop.py handoff <name>
python3 frinkloop.py handoff <name> --push
python3 frinkloop.py wake <name>
```

Compatibility shell scripts live in `scripts/`, but the Python CLI is the primary interface.

## Project Layout

```text
FrinkLoop/
├── frinkloop.py              # CLI entry point
├── agents/                   # role prompts
├── core/                     # loop, memory, LLM, contracts, GitHub, handoff
├── config/defaults.yaml      # documented defaults
├── templates/                # starter scaffolds
├── projects/_template/       # base project template
├── tests/                    # core test suite
├── docs/                     # planning notes
└── FRINKLOOP_PLAY.md         # alternate Claude Code playbook
```

Generated user projects live in `projects/<name>/`. They are ignored by git by default so this repo can be shared publicly without leaking local app code.

## Project Memory

Each generated project uses:

```text
projects/my-app/
├── BRIEF.md
├── HANDOFF.md
├── src/
├── tests/
└── memory/
    ├── plan.md
    ├── tasks.json
    ├── decisions.md
    ├── blockers.md
    ├── qa_report.md
    ├── research/
    └── agent_logs/
```

`tasks.json` is the live queue. `decisions.md`, `blockers.md`, and `qa_report.md` are the durable trail that makes the loop inspectable.

## Writing A Brief

`python3 frinkloop.py new <name>` creates a brief interactively. A manual `BRIEF.md` can be as simple as:

```markdown
# Project Brief

## What to build
Build a tiny CRM for solo consultants.

## Key requirements
- Add, edit, and archive contacts
- Track follow-up reminders
- Search by company or person

## Tech preferences
FastAPI, SQLite, simple HTML templates

## Done means
The app runs locally, has tests for core flows, and includes setup docs.

## Out of scope
No payments, teams, or hosted deployment in v1.
```

## Configuration

Important `.env` values:

```bash
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=...
GITHUB_TOKEN=...
OBSIDIAN_VAULT_PATH=/absolute/path/to/vault
DEFAULT_STACK=TypeScript
```

`GITHUB_TOKEN` and `OBSIDIAN_VAULT_PATH` are optional. Provider-specific keys are only required for the provider you choose.

## Safety Notes

- Do not commit `.env`, generated project code, logs, or memory state with secrets.
- Review agent commits before pushing real projects.
- Start with `--dry-run` when changing prompts, tools, or loop logic.
- Keep generated projects in private repos unless you intentionally want them public.
- Local Ollama models are useful for cheap iteration, but smaller models may need tighter briefs and smaller tasks.

## Development

Run the test suite:

```bash
pytest -q
```

Current local status:

```text
22 tests passing
```

Useful checks before a public push:

```bash
git status --short
rg -n "FIXME|Agent[O]S|Dev[O]S|agent[o]s|dev[o]s"
pytest -q
```

## Easy Improvement Plan

Small, high-impact improvements for contributors:

1. Add a `frinkloop doctor` command that validates Python version, provider env, Git, and optional GitHub/Obsidian setup.
2. Add a `frinkloop clean` command that removes local caches and generated logs safely.
3. Add example briefs in `examples/` for web app, CLI, API, and scraper projects.
4. Add provider-specific setup snippets for Ollama, OpenRouter, Groq, Gemini, and Anthropic.
5. Add a one-command public-readiness check that runs tests and scans for secrets/stale names.
6. Make `templates/` more complete so generated projects start with runnable tests.

## Contributing

This repo is easiest to improve in three places:

- `agents/` for behavior changes
- `core/` for loop/runtime changes
- `templates/` for better generated project starting points

Keep changes small, run `pytest -q`, and document any behavior change in this README or `config/defaults.yaml`.

## License

No license file is included yet. Add one before publishing if you want others to reuse, fork, or redistribute the code with clear terms.
