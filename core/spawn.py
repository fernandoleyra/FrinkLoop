"""
core/spawn.py — Agent launcher

Loads an agent's definition, builds its context window, and calls Claude.
Each agent gets: its role definition + project memory + the specific task.
"""

import os
from pathlib import Path
from typing import Any

import anthropic

# Root of the agent-os system (where this file lives)
AGENT_OS_ROOT = Path(__file__).parent.parent


def spawn_agent(
    agent: str,
    task: dict,
    project_path: Path,
    dry_run: bool = False,
) -> str:
    """
    Spawn an agent to execute a task.

    Args:
        agent: Agent name (orchestrator | developer | qa | critic | researcher)
        task: Task dict from tasks.json
        project_path: Path to the current project directory
        dry_run: If True, print what would happen but don't call the API

    Returns:
        Agent's output as a string
    """

    # 1. Load agent definition
    agent_def_path = AGENT_OS_ROOT / "agents" / f"{agent}.md"
    if not agent_def_path.exists():
        raise FileNotFoundError(f"Agent definition not found: {agent_def_path}")

    agent_definition = agent_def_path.read_text()

    # 2. Build project context (what this agent needs to know)
    context = _build_context(agent, task, project_path)

    # 3. Build the system prompt
    system_prompt = f"""
{agent_definition}

---

## Current Project Context

{context}

---

## Important Rules
- You have full access to read and write files in the project directory
- Write all code to `src/`, all tests to `tests/`, all notes to `memory/`
- When you complete your task, explicitly state: "TASK COMPLETE: [brief summary]"
- If you cannot complete the task, explicitly state: "TASK BLOCKED: [reason]"
- Do not ask the user questions — make decisions and proceed
""".strip()

    # 4. Build user message
    user_message = _build_user_message(task)

    if dry_run:
        print(f"\n[DRY RUN] Would spawn agent: {agent}")
        print(f"[DRY RUN] Task: {task.get('id')} — {task.get('input', '')[:100]}")
        return "DRY_RUN_RESULT"

    # 5. Call Claude
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    output = response.content[0].text

    # 6. Save agent output to memory
    _save_agent_output(agent, task, output, project_path)

    return output


def _build_context(agent: str, task: dict, project_path: Path) -> str:
    """Build the relevant context for an agent based on its role."""
    parts = []

    # Always include: current task
    parts.append(f"**Your task (ID: {task.get('id', 'T?')}):**\n{task.get('input', '')}")

    if task.get("instruction"):
        parts.append(f"**Special instructions:**\n{task['instruction']}")

    if task.get("acceptance"):
        parts.append(f"**Acceptance criteria:**\n{task['acceptance']}")

    # Always include: project decisions
    decisions_path = project_path / "memory" / "decisions.md"
    if decisions_path.exists():
        parts.append(f"**Architectural decisions so far:**\n{decisions_path.read_text()[:2000]}")

    # Role-specific context
    if agent == "developer":
        # Developer needs: relevant research + existing code structure
        research_dir = project_path / "memory" / "research"
        if research_dir.exists():
            for f in research_dir.glob("*.md"):
                parts.append(f"**Research ({f.stem}):**\n{f.read_text()[:1500]}")

        src_structure = _get_directory_tree(project_path / "src")
        if src_structure:
            parts.append(f"**Current src/ structure:**\n{src_structure}")

    elif agent == "qa":
        # QA needs: the output file to test
        output_file = task.get("output", "")
        if output_file:
            output_path = project_path / output_file
            if output_path.exists():
                parts.append(f"**File to test ({output_file}):**\n```\n{output_path.read_text()[:3000]}\n```")

    elif agent == "critic":
        # Critic needs: the code + QA report
        qa_report_path = project_path / "memory" / "qa_report.md"
        if qa_report_path.exists():
            parts.append(f"**QA Report:**\n{qa_report_path.read_text()[:2000]}")

        output_file = task.get("output", "")
        if output_file:
            output_path = project_path / output_file
            if output_path.exists():
                parts.append(f"**Code to review:**\n```\n{output_path.read_text()[:4000]}\n```")

    elif agent == "orchestrator":
        # Orchestrator needs: full memory picture
        blockers_path = project_path / "memory" / "blockers.md"
        if blockers_path.exists():
            parts.append(f"**Current blockers:**\n{blockers_path.read_text()}")

        tasks_path = project_path / "memory" / "tasks.json"
        if tasks_path.exists():
            parts.append(f"**Current tasks.json:**\n{tasks_path.read_text()[:3000]}")

    elif agent == "researcher":
        # Researcher just needs the question — already in task input
        pass

    return "\n\n".join(parts)


def _build_user_message(task: dict) -> str:
    """Build the user-facing message for the agent."""
    return (
        f"Execute task {task.get('id', 'T?')}.\n\n"
        f"Task type: {task.get('type', 'unknown')}\n"
        f"Task: {task.get('input', '')}\n\n"
        "Remember:\n"
        "- End your response with 'TASK COMPLETE: [summary]' if done\n"
        "- End with 'TASK BLOCKED: [reason]' if you cannot proceed\n"
        "- Write all output files before declaring complete"
    )


def _save_agent_output(agent: str, task: dict, output: str, project_path: Path) -> None:
    """Save agent output to memory for traceability."""
    log_dir = project_path / "memory" / "agent_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{timestamp}_{agent}_{task.get('id', 'T0')}.md"

    log_file.write_text(
        f"# Agent Log: {agent} — {task.get('id')}\n"
        f"Timestamp: {timestamp}\n\n"
        f"## Task\n{task.get('input', '')}\n\n"
        f"## Output\n{output}\n"
    )


def _get_directory_tree(path: Path, indent: int = 0) -> str:
    """Return a simple directory tree as a string."""
    if not path.exists():
        return ""

    lines = []
    prefix = "  " * indent

    for item in sorted(path.iterdir()):
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        if item.is_dir():
            lines.append(f"{prefix}{item.name}/")
            lines.append(_get_directory_tree(item, indent + 1))
        else:
            lines.append(f"{prefix}{item.name}")

    return "\n".join(filter(None, lines))
