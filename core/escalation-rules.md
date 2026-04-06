# Escalation Rules — When to Stop and Talk to the Human

## The Prime Directive
Do NOT interrupt the human unless a rule below is triggered.
Every interruption has a cost. Avoid it.

---

## Hard Escalation (ALWAYS stop)

| Trigger | Action |
|---|---|
| Same task fails 5+ times in a row | Stop. Report task_id, all errors, all attempts. |
| Agents disagree on architecture for 3+ loops | Stop. Present options, ask human to decide. |
| A security vulnerability is found | Stop immediately. Describe the vulnerability. |
| A decision requires spending real money | Stop. Never authorize cloud spend, API costs, etc. |
| Any action would delete or overwrite production data | Stop. Confirm explicitly. |
| Legal or licensing concern discovered | Stop. Flag it. |

---

## Soft Escalation (stop after current milestone)

| Trigger | Action |
|---|---|
| Scope creep detected (task requires 2x more than planned) | Finish current task, then report before next milestone. |
| A required external service is unavailable | Finish what you can, report the blocker. |
| Milestone 1 complete (first checkpoint) | Optional — report progress if human asked for updates. |

---

## Never Escalate For

- Normal test failures (create fix_task and continue)
- Lint warnings (fix them silently)
- Minor style decisions (follow existing conventions)
- Choosing between equivalent libraries (pick the simpler one, log the choice)
- Slow progress (agents are slower than humans, that is expected)

---

## Escalation Message Format

When you escalate, write this exact format:

  ESCALATION REQUIRED
  Trigger: <which rule was hit>
  Project: <project name>
  Task: <task_id>
  Status: <what was completed before stopping>
  Problem: <clear description of what went wrong or is needed>
  What I tried: <list of attempts if applicable>
  Options available: <if a decision is needed, list the options>
  Recommended: <your recommendation if you have one>
  Awaiting: <exactly what you need from the human to continue>
