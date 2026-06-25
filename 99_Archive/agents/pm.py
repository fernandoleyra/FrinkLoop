"""
NEXUS — PM Agent
The user's primary contact. Runs the structured intake interview,
maintains the living spec, dispatches sprints, and drives the team
toward MVP without stopping unless asked.
"""

import anthropic
import json
import sys
from pathlib import Path
from datetime import datetime

# ── Bootstrap ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tools import TOOLS, dispatch_tool
from agents.shared import (
    get_client, load_prompt, load_config,
    save_spec, load_spec,
    log_sprint, load_sprint_log,
    save_artifact, load_artifacts,
    log_decision,
)
from agents.project_lead import run as run_project_lead
from agents.rd import run as run_rd
from agents.engineering import run as run_engineering
from agents.ux_design import run as run_ux_design
from agents.data_analyst import run as run_data_analyst
from agents.product_visionary import run as run_product_visionary
from agents.qa_security import run as run_qa_security
from agents.devops import run as run_devops
from agents.biz_strategist import run as run_biz_strategist

CLIENT = get_client()
SYSTEM = load_prompt("pm")
CONFIG = load_config()

# ── Intake interview ──────────────────────────────────────────────────────────

INTAKE_PROMPT = """
You are the PM of NEXUS, an elite AI software development firm.
A new client just sent you this briefing:

{briefing}

Your job is to conduct a structured intake interview to clarify:

1. WHAT — What is the product? Who are the users? What problem does it solve?
2. HOW — What tech constraints exist? What integrations are needed? What's the scale?
3. OUTPUT — What defines MVP? What does "done" look like for the first milestone?
4. TIMELINE — What's the urgency? Are there phases or a single sprint?
5. RISKS — What assumptions are you making? What could kill this?

Ask no more than 5 sharp, structured questions. Make each one count.
After the user answers, synthesize a project spec in this exact format:

---SPEC---
Project: <name>
Vision: <one paragraph>
Users: <who>
MVP Definition: <clear, testable criteria>
Stack Constraints: <any hard requirements>
Key Features (ranked):
  1. ...
  2. ...
Open Questions: <anything still unclear>
Sprint 1 Goal: <specific, shippable deliverable>
---END SPEC---
"""

def run_intake(briefing: str) -> str:
    """Run the structured intake interview with the user."""
    print("\n" + "="*60)
    print("  NEXUS — Initializing project intake")
    print("="*60 + "\n")

    messages = [{"role": "user", "content": INTAKE_PROMPT.format(briefing=briefing)}]

    # First PM response: structured questions
    response = CLIENT.messages.create(
        model=CONFIG["model"]["name"],
        max_tokens=2048,
        system=SYSTEM,
        messages=messages,
    )
    pm_questions = response.content[0].text
    print(f"\n📋 PM:\n{pm_questions}\n")

    # Collect user answers
    print("─"*60)
    print("Your answers (press Enter twice when done):")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    user_answers = "\n".join(lines[:-1] if lines[-1] == "" else lines)

    # PM synthesizes spec
    messages += [
        {"role": "assistant", "content": pm_questions},
        {"role": "user", "content": user_answers},
        {"role": "user", "content": "Now synthesize the project spec in the exact format requested."}
    ]

    response = CLIENT.messages.create(
        model=CONFIG["model"]["name"],
        max_tokens=4096,
        system=SYSTEM,
        messages=messages,
    )
    spec_text = response.content[0].text
    save_spec(spec_text)

    print(f"\n✅ Spec captured. Handing to Project Lead for review...\n")
    return spec_text, user_answers


# ── Sprint orchestration ───────────────────────────────────────────────────────

SPRINT_PLAN_PROMPT = """
You are the PM of NEXUS.

Current project spec:
{spec}

Sprint history:
{sprint_log}

Artifacts produced so far:
{artifacts}

Your job: plan the NEXT sprint.
Decide which agents to activate and in what order for maximum value.
Available agents: rd, engineering, ux_design, data_analyst, product_visionary, qa_security, devops, biz_strategist.

Output a sprint plan as JSON:
{{
  "sprint_number": N,
  "goal": "what this sprint ships",
  "agents": [
    {{"name": "agent_name", "task": "specific task for this agent", "depends_on": []}}
  ],
  "mvp_progress": "X%",
  "stop_condition": "what would make us stop this sprint early"
}}
"""

def plan_sprint(spec: str) -> dict:
    """PM plans the next sprint."""
    sprint_log = load_sprint_log()
    artifacts = load_artifacts()

    messages = [{
        "role": "user",
        "content": SPRINT_PLAN_PROMPT.format(
            spec=spec,
            sprint_log=json.dumps(sprint_log, indent=2),
            artifacts=json.dumps(artifacts, indent=2),
        )
    }]

    response = CLIENT.messages.create(
        model=CONFIG["model"]["name"],
        max_tokens=2048,
        system=SYSTEM,
        messages=messages,
    )

    text = response.content[0].text
    # Extract JSON
    start = text.find("{")
    end = text.rfind("}") + 1
    plan = json.loads(text[start:end])
    return plan


AGENT_DISPATCH = {
    "rd": run_rd,
    "engineering": run_engineering,
    "ux_design": run_ux_design,
    "data_analyst": run_data_analyst,
    "product_visionary": run_product_visionary,
    "qa_security": run_qa_security,
    "devops": run_devops,
    "biz_strategist": run_biz_strategist,
}


def run_sprint(sprint_plan: dict, spec: str) -> dict:
    """Execute a sprint: run agents in order, collect outputs."""
    sprint_num = sprint_plan["sprint_number"]
    print(f"\n{'='*60}")
    print(f"  Sprint {sprint_num}: {sprint_plan['goal']}")
    print(f"  MVP progress: {sprint_plan['mvp_progress']}")
    print(f"{'='*60}\n")

    results = {}
    completed = set()

    for task in sprint_plan["agents"]:
        agent_name = task["name"]
        agent_task = task["task"]
        deps = task.get("depends_on", [])

        # Check dependencies
        dep_context = "\n".join([
            f"[{d} output]: {results[d][:500]}..."
            for d in deps if d in results
        ])

        full_task = f"{agent_task}"
        if dep_context:
            full_task += f"\n\nContext from upstream agents:\n{dep_context}"

        print(f"  → [{agent_name.upper()}] {agent_task[:60]}...")

        agent_fn = AGENT_DISPATCH.get(agent_name)
        if agent_fn:
            try:
                output = agent_fn(task=full_task, spec=spec, sprint=sprint_num)
                results[agent_name] = output
                completed.add(agent_name)
                log_decision(agent_name, sprint_num, agent_task, output[:1000])
            except Exception as e:
                results[agent_name] = f"ERROR: {e}"
                print(f"    ⚠ {agent_name} failed: {e}")

    log_sprint(sprint_num, sprint_plan["goal"], results)
    return results


# ── MVP check ─────────────────────────────────────────────────────────────────

MVP_CHECK_PROMPT = """
You are the PM of NEXUS. Assess whether MVP has been reached.

Project spec:
{spec}

All sprint results:
{sprint_log}

All artifacts produced:
{artifacts}

Answer in JSON:
{{
  "mvp_reached": true/false,
  "mvp_percentage": 0-100,
  "missing": ["list of what's still missing"],
  "recommendation": "continue | pause_for_review | done"
}}
"""

def check_mvp(spec: str) -> dict:
    sprint_log = load_sprint_log()
    artifacts = load_artifacts()
    response = CLIENT.messages.create(
        model=CONFIG["model"]["name"],
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": MVP_CHECK_PROMPT.format(
            spec=spec,
            sprint_log=json.dumps(sprint_log, indent=2),
            artifacts=json.dumps(artifacts, indent=2),
        )}]
    )
    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


# ── User status update ─────────────────────────────────────────────────────────

def print_status_update(sprint_num: int, sprint_results: dict, mvp_check: dict):
    print(f"\n{'─'*60}")
    print(f"📊 Sprint {sprint_num} complete")
    print(f"   MVP progress: {mvp_check['mvp_percentage']}%")
    if mvp_check.get("missing"):
        print(f"   Still needed: {', '.join(mvp_check['missing'][:3])}")
    print(f"   Agents that ran: {', '.join(sprint_results.keys())}")
    print(f"   Artifacts in: outputs/")
    print(f"{'─'*60}")

    if mvp_check["recommendation"] == "done":
        print("\n🎉 MVP REACHED. Drafting handoff report...\n")
    elif mvp_check["recommendation"] == "pause_for_review":
        print("\n⏸  Pausing for your review. Press Enter to continue or type 'stop' to exit.\n")
        inp = input().strip().lower()
        if inp == "stop":
            return False
    return True


# ── Main loop ─────────────────────────────────────────────────────────────────

def run(briefing: str = None):
    """Main NEXUS entrypoint."""
    # Accept briefing from CLI or prompt
    if not briefing:
        print("\n📥 Paste your project briefing (press Enter twice when done):\n")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        briefing = "\n".join(lines[:-1] if lines and lines[-1] == "" else lines)

    # Phase 1: Intake
    spec_text, user_answers = run_intake(briefing)

    # Phase 2: Project Lead reviews and stress-tests the spec
    print("\n🔥 Project Lead reviewing spec (devil's advocate mode)...\n")
    pl_review = run_project_lead(
        task=f"Review this spec and stress-test it. Identify risks, gaps, and flawed assumptions.\n\nSPEC:\n{spec_text}",
        spec=spec_text,
        sprint=0,
    )
    print(f"\n🎯 Project Lead:\n{pl_review[:800]}...\n")

    # Sprint loop
    max_sprints = CONFIG["iteration"]["max_sprints"]
    for sprint_num in range(1, max_sprints + 1):
        spec = load_spec()

        # Plan sprint
        sprint_plan = plan_sprint(spec)

        # Project Lead reviews plan
        print(f"\n🔥 Project Lead reviewing sprint {sprint_num} plan...")
        pl_sprint_review = run_project_lead(
            task=f"Review sprint plan. Approve or flag issues.\n\n{json.dumps(sprint_plan, indent=2)}",
            spec=spec,
            sprint=sprint_num,
        )
        print(f"   PL: {pl_sprint_review[:200]}...\n")

        # Execute sprint
        sprint_results = run_sprint(sprint_plan, spec)

        # Check MVP
        mvp_check = check_mvp(spec)
        should_continue = print_status_update(sprint_num, sprint_results, mvp_check)

        if not should_continue or mvp_check["recommendation"] == "done":
            break

    # Final handoff
    _write_handoff_report()


def _write_handoff_report():
    spec = load_spec()
    sprint_log = load_sprint_log()
    artifacts = load_artifacts()

    report = f"""# NEXUS Project Handoff Report
Generated: {datetime.now().isoformat()}

## Project Spec
{spec}

## Sprints Completed
{json.dumps(sprint_log, indent=2)}

## Artifacts Produced
{json.dumps(artifacts, indent=2)}

## Next Steps
See outputs/ for all generated code and documentation.
"""
    Path("outputs/HANDOFF.md").write_text(report)
    print("📄 Handoff report written to outputs/HANDOFF.md")


if __name__ == "__main__":
    briefing = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    run(briefing)
