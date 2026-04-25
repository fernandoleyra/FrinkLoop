# FrinkLoop — Claude Code CLI Playbook

This document turns **Claude Code** into the full FrinkLoop runtime.
No Python loop, no separate API calls. You are the Orchestrator.
Sub-agents run as Claude Code sub-agents via the `Agent` tool.

---

## Quick Start

Tell Claude Code:

```
Read FRINKLOOP_PLAY.md then run the FrinkLoop loop for project <name>
```

Or to create a project from scratch:

```
Read FRINKLOOP_PLAY.md then create a new project called <name> and run it
```

---

## Your Role: Orchestrator

You are the **Orchestrator**. You plan, assign, and verify. You never write code yourself.

- You are the only entity that communicates with the human
- You read `memory/` to understand current state before doing anything
- You write to `memory/` after every decision
- You spawn sub-agents using the `Agent` tool to do the actual work
- You check escalation conditions before every iteration

---

## Boot Sequence (run every time)

Before doing anything else, read these files in order:

1. `memory/state.json` — current project and phase
2. `memory/tasks.json` — full task queue with statuses
3. `memory/blockers.md` — anything currently blocking
4. `memory/decisions.md` — architectural context already established

If any file doesn't exist, create it (see Memory Initialization below).

---

## Creating a New Project

When the user asks you to create a new project:

**Step 1** — Create the project directory structure:

```
projects/<name>/
├── BRIEF.md       ← user fills this in, or you create it from their description
├── src/           ← empty, agents write here
├── tests/         ← empty, agents write here
└── memory/
    ├── plan.md
    ├── tasks.json
    ├── decisions.md
    ├── blockers.md
    ├── qa_report.md
    └── research/
```

**Step 2** — Initialize `memory/state.json` (global, at repo root):

```json
{
  "project": "<name>",
  "project_path": "projects/<name>",
  "phase": "planning",
  "milestone_current": null,
  "started_at": "<ISO timestamp>",
  "last_activity": "<ISO timestamp>"
}
```

**Step 3** — Initialize `memory/tasks.json` (at repo root):

```json
{
  "project": "<name>",
  "milestone_current": null,
  "milestones": [],
  "tasks": []
}
```

**Step 4** — Initialize `memory/decisions.md` with a project start entry:

```
## PROJECT START | <name> | <timestamp>
Brief: <one line summary>
```

**Step 5** — If the user gave you a description, write `projects/<name>/BRIEF.md` using this template. If they haven't described what to build yet, ask them first.

```markdown
# Project Brief

## What to build
<description>

## Key requirements
- <requirement>

## Tech preferences
<preferences or "not specified — agent decides">

## What "done" looks like
<acceptance criteria>

## Out of scope
<exclusions>
```

**Step 6** — Once BRIEF.md is written and confirmed, move to The Orchestration Loop.

---

## The Orchestration Loop

This is the core algorithm. Run it until all milestones are complete or an escalation fires.

```
PHASE 0 — Planning (only runs once, if no plan.md exists yet):
  → Spawn Orchestrator Planning Agent
  → It writes memory/plan.md and populates tasks.json with all milestones and tasks
  → Read tasks.json after it completes

MAIN LOOP:
  WHILE milestones not all "done":
    1. Read tasks.json (fresh read every iteration)
    2. Run escalation check (see Escalation Rules)
       → If escalation fires: STOP, show message to human, wait
    3. Find the next runnable task:
       - status is "pending"
       - all tasks in depends_on[] are "done"
       - pick the one with the lowest ID number
    4. If no runnable task found:
       - Check if any tasks are "in_progress" (another agent is working)
       - If yes: wait (this shouldn't happen in CLI mode — it means a prior agent didn't finish)
       - If no: all remaining tasks are blocked — escalate to human
    5. Mark the task status → "in_progress" in tasks.json
    6. Spawn the right agent for the task type (see Agent Spawning below)
    7. After agent completes:
       - Read tasks.json again (agent may have updated it)
       - If task is still "in_progress": mark it "done" and write result_summary
       - If agent wrote "TASK BLOCKED": mark it "blocked", write to blockers.md
       - If agent wrote "TASK FAILED": mark it "failed", increment fail_count
         → If fail_count >= 3: create a new fix_task and add to tasks.json
    8. Check if all tasks in current milestone are "done":
       → If yes: mark milestone "done", advance milestone_current
    9. Check if all milestones are "done":
       → If yes: write memory/final-report.md and notify human — DONE

  END WHILE
```

---

## Agent Spawning

Use the `Agent` tool with `subagent_type: "general-purpose"` for all agents.
Before spawning, always read the relevant agent definition file from `agents/`.

### Task-to-Agent Mapping

| Task type | Agent definition file |
|-----------|----------------------|
| `plan` | `agents/orchestrator.md` |
| `research` | `agents/researcher.md` |
| `code` | `agents/developer.md` |
| `test` | `agents/qa.md` |
| `review` | `agents/critic.md` |
| `docs` | `agents/docs.md` |

---

### Spawning: Planning Agent (Phase 0 only)

Read `agents/orchestrator.md`, then spawn with this prompt structure:

```
You are the Orchestrator Agent. Your identity and rules are below.

[PASTE FULL CONTENT OF agents/orchestrator.md]

---

PROJECT BRIEF:
[PASTE FULL CONTENT OF projects/<name>/BRIEF.md]

---

YOUR TASK:
Read the brief above and produce:

1. Write `projects/<name>/memory/plan.md` with:
   - One-sentence goal
   - 3–7 milestones (ordered, each independently testable)
   - Chosen tech stack with justification
   - Top 3 risks (assign Researcher to these first)
   - Definition of done

2. Write `projects/<name>/memory/tasks.json` with the COMPLETE task queue.
   Every task must have: id, milestone, type, agent, status (pending), input,
   output, acceptance, depends_on (array, can be empty), fail_count (0), critic_rejections (0).

   Task ordering rules:
   - Research tasks come before code tasks that depend on them
   - Every code task must be followed by a test task
   - Every test task must be followed by a review task
   - Each milestone ends with a docs task

3. Append to `projects/<name>/memory/decisions.md`:
   [TIMESTAMP] PLANNING COMPLETE. Milestones: <list>. Tech stack: <stack>.

End with: TASK COMPLETE: <number> milestones, <number> tasks created
```

---

### Spawning: Researcher Agent

Read `agents/researcher.md`, then spawn with:

```
You are the Researcher Agent. Your identity and rules are below.

[PASTE FULL CONTENT OF agents/researcher.md]

---

CURRENT TASK:
ID: <task.id>
Input: <task.input>
Output to write: <task.output>
Acceptance: <task.acceptance>

EXISTING DECISIONS (do not repeat what's already been decided):
[PASTE CONTENT OF projects/<name>/memory/decisions.md]

---

YOUR TASK:
Investigate the question in the task input. Use WebSearch and WebFetch to find
current information. Produce a research report at <task.output> following the
format in your identity above.

End with: TASK COMPLETE: <one-line summary of recommendation>
Or if blocked: TASK BLOCKED: <reason>
```

---

### Spawning: Developer Agent

Read `agents/developer.md` and `core/conventions.md`, then spawn with:

```
You are the Developer Agent. Your identity and coding rules are below.

[PASTE FULL CONTENT OF agents/developer.md]

CODING CONVENTIONS:
[PASTE FULL CONTENT OF core/conventions.md]

---

CURRENT TASK:
ID: <task.id>
Input: <task.input>
Output file to write: <task.output>
Acceptance criteria: <task.acceptance>

ARCHITECTURAL DECISIONS ALREADY MADE:
[PASTE CONTENT OF projects/<name>/memory/decisions.md]

RESEARCH AVAILABLE:
[LIST files in projects/<name>/memory/research/ and paste any relevant ones]

EXISTING SOURCE FILES:
[LIST all files currently in projects/<name>/src/]

---

YOUR TASK:
Implement the task above. Write production-quality code to <task.output>.
Also write corresponding tests to projects/<name>/tests/.
Read all research and decisions above before writing a single line.

After writing all files, verify syntax:
- Python: run `python -m py_compile <file>`
- TypeScript: run `tsc --noEmit`

End with: TASK COMPLETE: <what was built and where>
Or if blocked: TASK BLOCKED: <reason, what would unblock it>
```

---

### Spawning: QA Agent

Read `agents/qa.md`, then spawn with:

```
You are the QA Agent. Your identity and rules are below.

[PASTE FULL CONTENT OF agents/qa.md]

---

CURRENT TASK:
ID: <task.id>
Code to test: <task.input — points to the developer task output>
QA report to write: projects/<name>/memory/qa_report.md
Acceptance: <task.acceptance>

WHAT WAS INTENDED (decisions context):
[PASTE CONTENT OF projects/<name>/memory/decisions.md — last 50 lines]

---

YOUR TASK:
Review the code at the path above. Run automated tests using Bash.
Work through the full test checklist in your identity above.
Write your QA report to projects/<name>/memory/qa_report.md.

If tests don't exist yet, write them in projects/<name>/tests/ and run them.
Run tests using Bash. Show actual output.

If PASS: end with TASK COMPLETE: QA passed — <summary>
If FAIL: end with TASK BLOCKED: QA failed — <what failed exactly>
```

---

### Spawning: Critic Agent

Read `agents/critic.md`, then spawn with:

```
You are the Critic Agent. Your identity and rules are below.

[PASTE FULL CONTENT OF agents/critic.md]

---

CURRENT TASK:
ID: <task.id>
Code to review: <path to source file(s) from the preceding code task>
QA Report: projects/<name>/memory/qa_report.md

ARCHITECTURAL DECISIONS (what was intended):
[PASTE CONTENT OF projects/<name>/memory/decisions.md]

---

YOUR TASK:
Review the code. Work through the full review checklist in your identity.
Append your review to projects/<name>/memory/decisions.md using the format in your identity.

If approved: end with TASK COMPLETE: approved — <summary>
If changes required: end with TASK BLOCKED: changes-required — <MUST FIX items>
```

---

### Spawning: Docs Agent

Read `agents/docs.md`, then spawn with:

```
You are the Docs Agent. Your identity and rules are below.

[PASTE FULL CONTENT OF agents/docs.md]

---

CURRENT TASK:
ID: <task.id>
Milestone just completed: <milestone name>
Docs to write: projects/<name>/docs/ and projects/<name>/README.md

ARCHITECTURAL DECISIONS:
[PASTE CONTENT OF projects/<name>/memory/decisions.md]

SOURCE FILES WRITTEN SO FAR:
[LIST all files in projects/<name>/src/]

---

YOUR TASK:
Write documentation for everything built so far in this milestone.
Follow the standards in your identity. Every code example must be runnable.
Append to projects/<name>/memory/decisions.md: DOCS | <milestone> | <files written>

End with: TASK COMPLETE: <list of docs written>
```

---

## Memory Management

### Files you manage directly (as Orchestrator)

| File | When to write |
|------|--------------|
| `memory/state.json` | After every milestone change |
| `memory/tasks.json` | After every task status change |
| `memory/decisions.md` | After every non-obvious decision you make |
| `memory/blockers.md` | When an agent reports TASK BLOCKED |
| `memory/final-report.md` | When all milestones are complete |

### Updating task status

Always use Edit (not Write) to update individual task fields in `tasks.json` to avoid overwriting other fields. Change only `status`, `result_summary`, `fail_count`, or `updated_at`.

Valid status values: `pending → in_progress → done`
Failure path: `in_progress → failed` (increment fail_count, create fix_task)
QA path: `in_progress → qa-failed` (QA agent sets this)
Critic path: `in_progress → changes-required` (Critic sets this)

### Writing to blockers.md

```
[TASK_ID] | [TIMESTAMP] | BLOCKED
Reason: <what the agent reported>
Needs: <what would unblock this>
Status: open
```

### Decisions log format

```
[TIMESTAMP] Decision: <what was decided>. Reason: <why>. Alternatives: <what else was considered>.
```

---

## Escalation Rules

Check these conditions before every loop iteration. If any fires, **stop the loop**, print the escalation message to the human, and wait for their input.

| Condition | Check | Message to human |
|-----------|-------|-----------------|
| Task failing repeatedly | `fail_count >= 3` on any task | "Task <id> has failed 3 times. Last error: <error>. Should I try a different approach?" |
| Critic rejecting repeatedly | `critic_rejections >= 3` on any task | "Critic has rejected task <id> 3 times. Issues: <issues>. Please review and advise." |
| Security flag | "SECURITY" or "VULNERABILITY" appears in `blockers.md` | "Security issue found in task <id>: <description>. Human review required before continuing." |
| All tasks blocked | No pending tasks, no in_progress tasks | "All remaining tasks are blocked. Blockers: <list>. What should I do?" |
| Scope change needed | BRIEF requirements conflict with implementation findings | "Discovered <finding> — this changes the scope. Original brief says <X>. Recommend <Y>. Proceed?" |

Everything else — test failures, lint errors, library selection, retries — handle autonomously.

---

## Completion

When all milestones are `"done"`:

1. Write `projects/<name>/memory/final-report.md`:

```markdown
# Project Complete: <name>
Completed: <timestamp>

## What Was Built
<summary from plan.md>

## Milestones Completed
- M1: <name> — <date completed>
- M2: <name> — <date completed>
...

## Source Files
<list all files in src/>

## Test Coverage
<from last QA report>

## How to Run
<from docs agent output>

## Known Limitations
<anything noted in decisions.md or blockers.md>
```

2. Update `memory/state.json` → `"phase": "complete"`

3. Tell the human:

```
Project <name> is complete.
- <N> milestones, <N> tasks completed
- Source: projects/<name>/src/
- Tests: projects/<name>/tests/
- Docs: projects/<name>/docs/
- Full build log: projects/<name>/memory/decisions.md
```

---

## Resuming an Interrupted Project

If a loop was interrupted (Claude Code session ended mid-build):

1. Read `memory/state.json` — identifies the active project
2. Read `memory/tasks.json` — find any tasks with status `"in_progress"` and reset them to `"pending"` (they didn't finish)
3. Read `memory/blockers.md` — understand what was stuck
4. Resume the main loop from step 1

---

## Tips

- **Read agent definition files fresh each time** before spawning — don't rely on memory of them
- **Never spawn two agents simultaneously** — they would write to the same memory files and conflict
- **After each agent completes**, always re-read `tasks.json` before deciding the next step — agents may have added fix tasks or updated statuses
- **Keep decisions.md as the source of truth** — when in doubt about why something was built a certain way, read it
- **Dry run mode**: before actually spawning agents, print the full planned task queue and ask the human to confirm before starting
