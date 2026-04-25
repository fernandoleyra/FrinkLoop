"""
core/spawn.py — Agent launcher

Loads an agent's definition, builds its context window, and calls Claude.
Each agent gets: its role definition + project memory + the specific task.
"""

import os
from pathlib import Path
from typing import Any

from core.contracts import AgentResult, parse_agent_output
from core.llm import call_llm, call_llm_with_tools, is_local_provider
from core.tools import get_tools_for_agent, execute_tool

# Root of the FrinkLoop system.
FRINKLOOP_ROOT = Path(__file__).parent.parent


def spawn_agent(
    agent: str,
    task: dict,
    project_path: Path,
    dry_run: bool = False,
) -> AgentResult:
    """
    Spawn an agent to execute a task.

    Args:
        agent: Agent name (orchestrator | developer | qa | critic | researcher)
        task: Task dict from tasks.json
        project_path: Path to the current project directory
        dry_run: If True, print what would happen but don't call the API

    Returns:
        Parsed agent result with the raw output attached
    """

    # 1. Load agent definition
    agent_def_path = FRINKLOOP_ROOT / "agents" / f"{agent}.md"
    if not agent_def_path.exists():
        raise FileNotFoundError(f"Agent definition not found: {agent_def_path}")

    agent_definition = agent_def_path.read_text()

    # 2. Build project context (what this agent needs to know)
    compact_mode = is_local_provider()
    context = _build_context(agent, task, project_path, compact_mode=compact_mode)

    # 3. Build the system prompt
    system_prompt = _build_system_prompt(agent_definition, context, compact_mode=compact_mode)

    # 4. Build user message
    user_message = _build_user_message(task, compact_mode=compact_mode)

    if dry_run:
        print(f"\n[DRY RUN] Would spawn agent: {agent}")
        print(f"[DRY RUN] Task: {task.get('id')} — {task.get('input', '')[:100]}")
        return AgentResult(
            status="complete",
            summary="Dry run only",
            raw_output='RESULT_JSON: {"summary":"Dry run only","files_written":[],"tests_run":[],"followups":[]}\nTASK COMPLETE: Dry run only',
        )

    max_tokens = _max_tokens_for_task(task, compact_mode=compact_mode)
    tools = get_tools_for_agent(agent)
    executor = lambda name, inputs: execute_tool(name, inputs, project_path)
    output = call_llm_with_tools(system_prompt, user_message, tools, executor, max_tokens=max_tokens)

    # 6. Save agent output to memory
    _save_agent_output(agent, task, output, project_path)

    return parse_agent_output(output, task.get("type"))


def _build_system_prompt(agent_definition: str, context: str, *, compact_mode: bool = False) -> str:
    if compact_mode:
        return f"""
{agent_definition}

Context:
{context}

Rules:
- Write code in `src/`, tests in `tests/`, notes in `memory/`
- No questions to user
- Output one line:
- RESULT_JSON: {{"summary":"...","files_written":["..."],"tests_run":["..."],"followups":["..."],"blocker_reason":""}}
- End with TASK COMPLETE or TASK BLOCKED
""".strip()

    return f"""
{agent_definition}

---

## Current Project Context

{context}

---

## Important Rules
- Use the write_file, read_file, run_command, and append_file tools to interact with the filesystem
- Write all code to `src/`, all tests to `tests/`, all notes to `memory/`
- Run tests with run_command before declaring TASK COMPLETE — do not claim tests pass without running them
- When you complete your task, explicitly state: "TASK COMPLETE: [brief summary]"
- If you cannot complete the task, explicitly state: "TASK BLOCKED: [reason]"
- Before the terminal task marker, emit one single-line JSON payload exactly as:
- RESULT_JSON: {{"summary":"...","files_written":["..."],"tests_run":["..."],"followups":["..."],"blocker_reason":""}}
- Do not ask the user questions — make decisions and proceed
""".strip()


def _build_context(agent: str, task: dict, project_path: Path, *, compact_mode: bool = False) -> str:
    """Build the relevant context for an agent based on its role."""
    parts = []
    decisions_limit = 600 if compact_mode else 2000
    research_limit = 500 if compact_mode else 1500
    qa_file_limit = 1200 if compact_mode else 3000
    critic_code_limit = 1200 if compact_mode else 4000
    tasks_limit = 1200 if compact_mode else 3000

    # Always include: current task
    if compact_mode:
        parts.append(f"Task {task.get('id', 'T?')}: {task.get('input', '')}")
    else:
        parts.append(f"**Your task (ID: {task.get('id', 'T?')}):**\n{task.get('input', '')}")

    if task.get("instruction"):
        label = "Instructions" if compact_mode else "**Special instructions:**"
        parts.append(f"{label}\n{task['instruction']}")

    if task.get("acceptance"):
        label = "Acceptance" if compact_mode else "**Acceptance criteria:**"
        parts.append(f"{label}\n{task['acceptance']}")

    # Always include: project decisions
    decisions_path = project_path / "memory" / "decisions.md"
    if decisions_path.exists():
        label = "Decisions" if compact_mode else "**Architectural decisions so far:**"
        parts.append(f"{label}\n{decisions_path.read_text()[:decisions_limit]}")

    # Role-specific context
    if agent == "developer":
        # Developer needs: relevant research + existing code structure
        research_dir = project_path / "memory" / "research"
        if research_dir.exists():
            research_files = sorted(research_dir.glob("*.md"))
            if compact_mode:
                research_files = research_files[:2]
            for f in research_files:
                label = f"Research {f.stem}" if compact_mode else f"**Research ({f.stem}):**"
                parts.append(f"{label}\n{f.read_text()[:research_limit]}")

        src_structure = _get_directory_tree(project_path / "src")
        if src_structure:
            label = "src tree" if compact_mode else "**Current src/ structure:**"
            parts.append(f"{label}\n{src_structure}")

    elif agent == "qa":
        # QA needs: the output file to test
        output_file = task.get("output", "")
        if output_file:
            output_path = project_path / output_file
            if output_path.exists():
                label = f"File to test {output_file}" if compact_mode else f"**File to test ({output_file}):**"
                parts.append(f"{label}\n```\n{output_path.read_text()[:qa_file_limit]}\n```")

    elif agent == "critic":
        # Critic needs: the code + QA report
        qa_report_path = project_path / "memory" / "qa_report.md"
        if qa_report_path.exists():
            label = "QA report" if compact_mode else "**QA Report:**"
            parts.append(f"{label}\n{qa_report_path.read_text()[:decisions_limit]}")

        output_file = task.get("output", "")
        if output_file:
            output_path = project_path / output_file
            if output_path.exists():
                label = "Code to review" if compact_mode else "**Code to review:**"
                parts.append(f"{label}\n```\n{output_path.read_text()[:critic_code_limit]}\n```")

    elif agent == "orchestrator":
        # Orchestrator needs: full memory picture
        blockers_path = project_path / "memory" / "blockers.md"
        if blockers_path.exists():
            label = "Blockers" if compact_mode else "**Current blockers:**"
            parts.append(f"{label}\n{blockers_path.read_text()[:decisions_limit]}")

        tasks_path = project_path / "memory" / "tasks.json"
        if tasks_path.exists():
            label = "tasks.json" if compact_mode else "**Current tasks.json:**"
            parts.append(f"{label}\n{tasks_path.read_text()[:tasks_limit]}")

    elif agent == "researcher":
        # Researcher just needs the question — already in task input
        pass

    return "\n\n".join(parts)


def _build_user_message(task: dict, *, compact_mode: bool = False) -> str:
    """Build the user-facing message for the agent."""
    if task.get("type") == "plan":
        if compact_mode:
            return (
                f"Plan task {task.get('id', 'T?')}.\n"
                f"Brief: {task.get('input', '')}\n"
                "Return RESULT_JSON with keys: summary, plan_markdown, tasks_board, decisions_entry.\n"
                "Keep it lean: 3-5 milestones, under 12 tasks total, short acceptance criteria.\n"
                "Then end with TASK COMPLETE."
            )
        return (
            f"Execute planning task {task.get('id', 'T?')}.\n\n"
            f"Task: {task.get('input', '')}\n\n"
            "Use write_file to create these files directly:\n"
            "  1. memory/plan.md — milestones and acceptance criteria\n"
            "  2. memory/tasks.json — full task board (see schema below)\n"
            "  3. memory/decisions.md — initial architecture decisions\n\n"
            "tasks.json schema: {\"project\": \"<name>\", \"milestones\": [{\"id\": \"M1\", \"name\": \"...\", "
            "\"tasks\": [{\"id\": \"T01\", \"type\": \"code|research|test|review\", \"input\": \"...\", "
            "\"depends_on\": [], \"status\": \"pending\"}]}]}\n\n"
            "Keep the plan lean: 3–5 milestones, under 12 tasks total.\n"
            "After writing files, return RESULT_JSON with just {\"summary\": \"...\"}.\n"
            "Then end with 'TASK COMPLETE: [summary]'."
        )

    if compact_mode:
        return (
            f"Task {task.get('id', 'T?')} ({task.get('type', 'unknown')}): {task.get('input', '')}\n"
            "Return one RESULT_JSON line, then TASK COMPLETE or TASK BLOCKED.\n"
            "Be concise."
        )

    return (
        f"Execute task {task.get('id', 'T?')}.\n\n"
        f"Task type: {task.get('type', 'unknown')}\n"
        f"Task: {task.get('input', '')}\n\n"
        "Remember:\n"
        "- Emit a single-line RESULT_JSON payload before the final task marker\n"
        "- End your response with 'TASK COMPLETE: [summary]' if done\n"
        "- End with 'TASK BLOCKED: [reason]' if you cannot proceed\n"
        "- Write all output files before declaring complete"
    )


def _max_tokens_for_task(task: dict, *, compact_mode: bool = False) -> int:
    if not compact_mode:
        return 8192
    if task.get("type") == "plan":
        return 1800
    return 900


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
