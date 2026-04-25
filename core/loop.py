"""
core/loop.py — The autonomous iteration engine

This is the heart of FrinkLoop. It reads tasks.json, assigns agents,
executes work, and loops until the project is done or escalation triggers.

Usage:
    python3 core/loop.py --project <project-name>
    python3 core/loop.py --project firecrawl-clone --dry-run
"""

import os
import re
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from core.spawn import spawn_agent
from core.memory import Memory
from core.escalation import check_escalation
from core.obsidian import sync_project, vault_path_from_env
from core.github import commit_task, push_to_remote, open_issue_for_blocker
from core.contracts import AgentResult
from core.llm import call_llm
from core.models import Task, TaskBoard
import core.config as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("frinkloop")


# ─── Configuration (loaded from config/defaults.yaml) ────────────────────────

MAX_TASK_RETRIES   = cfg.get("loop", "max_task_retries",  5)
MAX_LOOP_ITERATIONS = cfg.get("loop", "max_iterations",   200)
LOOP_SLEEP_SECONDS  = cfg.get("loop", "sleep_seconds",    2)

AGENT_TASK_MAP = {
    "research":  "researcher",
    "code":      "developer",
    "test":      "qa",
    "review":    "critic",
    "plan":      "orchestrator",
}


def run_quality_gates(task: Task, project_path: Path, dry_run: bool = False) -> tuple[Optional[str], AgentResult | None, dict]:
    """Run QA and Critic sequentially for a completed code task."""
    gate_metadata: dict = {}

    qa_task = task.to_dict()
    qa_task["type"] = "test"
    qa_task["agent"] = "qa"
    qa_task["instruction"] = (
        f"Validate the implementation for task {task.id}. "
        "Write/update memory/qa_report.md with the findings. "
        "Return TASK COMPLETE only if the implementation passes QA. "
        "Return TASK FAILED for a QA rejection. "
        "Use RESULT_JSON.tests_run for the commands you executed."
    )
    qa_result = spawn_agent("qa", qa_task, project_path, dry_run=dry_run)
    gate_metadata["qa_summary"] = qa_result.summary
    gate_metadata["qa_tests_run"] = qa_result.tests_run
    if qa_result.status != "complete":
        return "qa", qa_result, gate_metadata

    critic_task = task.to_dict()
    critic_task["type"] = "review"
    critic_task["agent"] = "critic"
    critic_task["instruction"] = (
        f"Review the implementation for task {task.id} after QA pass. "
        "Append your findings to memory/decisions.md. "
        "Return TASK COMPLETE only if the code is approved. "
        "Return TASK FAILED if there are must-fix issues."
    )
    critic_result = spawn_agent("critic", critic_task, project_path, dry_run=dry_run)
    gate_metadata["critic_summary"] = critic_result.summary
    gate_metadata["critic_followups"] = critic_result.followups
    if critic_result.status != "complete":
        return "critic", critic_result, gate_metadata

    return None, None, gate_metadata


# ─── Main Loop ────────────────────────────────────────────────────────────────

def run_loop(project_name: str, dry_run: bool = False, no_hitl: bool = False) -> None:
    """Main autonomous loop. Runs until project is done or escalation triggers."""

    project_path = Path("projects") / project_name
    memory = Memory(project_path)

    log.info(f"Starting FrinkLoop loop for project: {project_name}")
    log.info(f"Project path: {project_path.resolve()}")

    if not (project_path / "BRIEF.md").exists():
        raise FileNotFoundError(
            f"No BRIEF.md found at {project_path}/BRIEF.md\n"
            "Create a BRIEF.md in your project folder to get started."
        )

    # ── Phase 0: Initial planning (if no plan exists yet) ────────────────────
    if not (project_path / "memory" / "plan.md").exists():
        log.info("No plan found — running Orchestrator to create initial plan...")
        brief = (project_path / "BRIEF.md").read_text()
        planning_result = spawn_agent(
            agent="orchestrator",
            task={
                "id": "T0",
                "type": "plan",
                "input": brief,
                "instruction": (
                    "Read this BRIEF and create:\n"
                    "1. memory/plan.md — milestones and acceptance criteria\n"
                    "2. memory/tasks.json — first batch of tasks\n"
                    "3. memory/decisions.md — initial architecture decisions\n"
                    "Use the project templates in templates/ if a matching one exists."
                ),
            },
            project_path=project_path,
            dry_run=dry_run,
        )
        _materialize_planning_artifacts(project_path, planning_result)
        _assert_planning_artifacts(project_path, planning_result)

    # ── Main Loop ─────────────────────────────────────────────────────────────
    for iteration in range(MAX_LOOP_ITERATIONS):
        log.info(f"─── Iteration {iteration + 1} ───────────────────────────────")

        # Compress decisions.md if it has grown too large
        compress_decisions_if_needed(project_path, memory)

        tasks = memory.load_tasks()
        if not tasks:
            _raise_missing_tasks_error(project_path)
            log.info("No tasks found. Waiting for Orchestrator to generate tasks...")
            time.sleep(LOOP_SLEEP_SECONDS)
            continue

        # Check escalation conditions
        escalation = check_escalation(tasks, memory)
        if escalation:
            log.warning(f"ESCALATION TRIGGERED: {escalation}")
            should_continue = handle_escalation_interactively(escalation, tasks, memory, project_path, dry_run, no_hitl=no_hitl)
            if not should_continue:
                notify_human(project_name, escalation, memory)
                return

        # Find next actionable task
        task = get_next_task(tasks)
        if task is None:
            if all_milestones_complete(tasks):
                log.info("✅ ALL MILESTONES COMPLETE")
                notify_human(
                    project_name,
                    "All milestones complete — project is ready.",
                    memory,
                    success=True
                )
                return
            else:
                log.info("No actionable tasks right now. Checking for blocked tasks...")
                handle_blocked_tasks(tasks, memory, project_path, dry_run)
                time.sleep(LOOP_SLEEP_SECONDS)
                continue

        # Execute the task
        log.info(f"Executing task {task.id}: [{task.type}] {task.input[:80]}...")
        memory.update_task_status(task.id, "in_progress")

        try:
            agent_name = AGENT_TASK_MAP.get(task.type, task.agent)
            result = spawn_agent(
                agent=agent_name,
                task=task.to_dict(),
                project_path=project_path,
                dry_run=dry_run,
            )
            if result.status == "blocked":
                memory.update_task_status(
                    task.id,
                    "blocked",
                    error=result.blocker_reason or result.summary,
                    metadata={
                        "files_written": result.files_written,
                        "tests_run": result.tests_run,
                        "followups": result.followups,
                    },
                )
                memory.write_blocker(task.id, result.blocker_reason or result.summary)
                log.warning(f"Task {task.id} blocked by {agent_name}: {result.summary}")
                time.sleep(LOOP_SLEEP_SECONDS)
                continue

            if result.status != "complete":
                raise RuntimeError(result.summary)

            task_metadata = {
                "files_written": result.files_written,
                "tests_run": result.tests_run,
                "followups": result.followups,
            }

            if task.type == "code":
                gate_name, gate_result, gate_metadata = run_quality_gates(task, project_path, dry_run=dry_run)
                task_metadata.update(gate_metadata)
                if gate_name and gate_result:
                    if gate_result.status == "blocked":
                        memory.update_task_status(
                            task.id,
                            "blocked",
                            error=gate_result.blocker_reason or gate_result.summary,
                            metadata=task_metadata,
                        )
                        memory.write_blocker(task.id, gate_result.blocker_reason or gate_result.summary)
                        log.warning(f"Task {task.id} blocked in {gate_name}: {gate_result.summary}")
                        time.sleep(LOOP_SLEEP_SECONDS)
                        continue

                    fail_count_after = memory.increment_fail_count(task.id)
                    if gate_name == "critic":
                        memory.increment_critic_rejections(task.id)

                    feedback = f"{gate_name} gate failed: {gate_result.summary}"

                    if fail_count_after >= MAX_TASK_RETRIES:
                        memory.update_task_status(
                            task.id, "blocked",
                            error=feedback,
                            metadata=task_metadata,
                        )
                        memory.write_blocker(task.id, feedback)
                        log.warning(f"Task {task.id} hit max retries ({fail_count_after}) in {gate_name} — blocking")
                    else:
                        _inject_feedback_and_reset(memory, task.id, feedback)
                        log.info(
                            f"Task {task.id} failed {gate_name} "
                            f"(attempt {fail_count_after}) — injecting feedback, retrying"
                        )
                    time.sleep(LOOP_SLEEP_SECONDS)
                    continue

            memory.update_task_status(
                task.id,
                "done",
                result=result.summary,
                metadata=task_metadata,
            )
            log.info(f"✓ Task {task.id} completed by {agent_name}")

            # Git commit for this task
            commit_task(project_path, task.to_dict())

            # Push to GitHub after each milestone completes
            tasks_now = memory.load_tasks()
            current_m = None
            if tasks_now:
                current_m = next(
                    (milestone for milestone in tasks_now.milestones if milestone.id == task.milestone),
                    None,
                )
            if current_m and current_m.status == "done":
                log.info(f"Milestone {current_m.id} complete — pushing to GitHub")
                push_to_remote(project_path)

            # Obsidian sync
            vault = vault_path_from_env()
            if vault:
                try:
                    sync_project(project_path, vault)
                    log.info(f"Obsidian vault synced → {vault}/FrinkLoop/{project_path.name}/")
                except Exception as e:
                    log.warning(f"Obsidian sync failed (non-fatal): {e}")

        except Exception as e:
            log.error(f"✗ Task {task.id} failed: {e}")
            fail_count = memory.increment_fail_count(task.id)

            if fail_count >= MAX_TASK_RETRIES:
                blocker_reason = f"Task failed {fail_count} times. Last error: {e}"
                memory.update_task_status(task.id, "blocked", error=blocker_reason)
                memory.write_blocker(task.id, blocker_reason)
                log.warning(f"Task {task.id} hit max retries ({fail_count}) — blocking")
                issue_url = open_issue_for_blocker(project_path, task.id, blocker_reason)
                if issue_url:
                    log.info(f"GitHub issue opened: {issue_url}")
            else:
                _inject_feedback_and_reset(memory, task.id, str(e))
                log.info(f"Task {task.id} failed (attempt {fail_count}) — injecting error context, retrying")

        time.sleep(LOOP_SLEEP_SECONDS)

    log.error(f"Hit maximum iterations ({MAX_LOOP_ITERATIONS}) — something may be stuck.")
    notify_human(project_name, f"Loop hit max iterations ({MAX_LOOP_ITERATIONS}). Check memory/blockers.md", memory)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_next_task(tasks: TaskBoard) -> Optional[Task]:
    """Find the next task that is ready to run (pending + dependencies met)."""
    all_done_ids = tasks.completed_task_ids()

    for milestone in tasks.milestones:
        if milestone.status == "done":
            continue
        for task in milestone.tasks:
            if task.status not in ("pending", ""):
                continue
            if all(dep in all_done_ids for dep in task.depends_on):
                return task

    return None


def all_milestones_complete(tasks: TaskBoard) -> bool:
    """Return True only when every milestone and every task is done."""
    for milestone in tasks.milestones:
        if milestone.status != "done":
            return False
        for task in milestone.tasks:
            if task.status != "done":
                return False
    return True


def handle_blocked_tasks(tasks: TaskBoard, memory: Memory, project_path: Path, dry_run: bool):
    """Ask the Orchestrator to resolve any blocked tasks."""
    blockers = memory.read_blockers()
    if blockers:
        log.info("Asking Orchestrator to resolve blockers...")
        spawn_agent(
            agent="orchestrator",
            task={
                "id": "T-resolve",
                "type": "plan",
                "input": blockers,
                "instruction": (
                    "Review memory/blockers.md and memory/tasks.json.\n"
                    "Resolve each blocker by either:\n"
                    "- Adding a research task to unblock it\n"
                    "- Making an architectural decision and updating decisions.md\n"
                    "- Splitting the task into smaller pieces\n"
                    "Update tasks.json with the resolution."
                ),
            },
            project_path=project_path,
            dry_run=dry_run,
        )


def handle_escalation_interactively(
    escalation: str,
    tasks: TaskBoard,
    memory: Memory,
    project_path: Path,
    dry_run: bool,
    no_hitl: bool = False,
) -> bool:
    """
    Present escalation options to the user and act on their choice.
    Returns True if the loop should continue, False if it should stop.
    In no_hitl mode, auto-skips the failing task and continues.
    """
    if no_hitl:
        failing_task = _find_failing_task(tasks)
        if failing_task:
            failing_task.status = "done"
            failing_task.result_summary = "Auto-skipped in noHITL mode"
            memory.save_tasks(tasks)
            memory.clear_blocker(failing_task.id)
            log.warning(f"noHITL: auto-skipped task {failing_task.id} — {escalation[:120]}")
        return True

    separator = "═" * 60
    print(f"\n{separator}")
    print("  FrinkLoop — NEEDS YOUR ATTENTION")
    print(separator)
    print()
    for line in escalation.splitlines():
        print(f"  {line}")
    print()

    # Find the failing task for context
    failing_task = _find_failing_task(tasks)

    print("  Options:")
    print("  [1] Add context and retry (you'll be prompted for a note)")
    print("  [2] Skip this task and continue")
    print("  [3] Replace with a different approach (you'll describe it)")
    print("  [4] View full error log")
    print("  [5] Stop loop — I'll handle this manually")
    print()

    while True:
        try:
            choice = input("  Choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        if choice == "1" and failing_task:
            try:
                context = input("  Your note for the agent: ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if context:
                # Append context to the task input and reset it
                failing_task.input = failing_task.input + f"\n\nHuman context: {context}"
                failing_task.status = "pending"
                failing_task.fail_count = 0
                failing_task.last_error = ""
                memory.save_tasks(tasks)
                memory.clear_blocker(failing_task.id)
                memory.log_decision(
                    f"Human unblocked task {failing_task.id}",
                    f"User added context: {context[:200]}",
                )
                log.info(f"Task {failing_task.id} reset with human context — continuing loop")
            return True

        elif choice == "2" and failing_task:
            failing_task.status = "done"
            failing_task.result_summary = "Skipped by human decision"
            memory.save_tasks(tasks)
            memory.clear_blocker(failing_task.id)
            memory.log_decision(
                f"Skipped task {failing_task.id}",
                "Human chose to skip this task during escalation",
            )
            log.info(f"Task {failing_task.id} skipped — continuing loop")
            return True

        elif choice == "3" and failing_task:
            try:
                approach = input("  Describe the new approach: ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if approach:
                failing_task.input = approach
                failing_task.status = "pending"
                failing_task.fail_count = 0
                failing_task.last_error = ""
                memory.save_tasks(tasks)
                memory.clear_blocker(failing_task.id)
                memory.log_decision(
                    f"Replaced task {failing_task.id} with new approach",
                    f"Human replaced approach: {approach[:200]}",
                )
                log.info(f"Task {failing_task.id} replaced — continuing loop")
            return True

        elif choice == "4":
            log_dir = project_path / "memory" / "agent_logs"
            if log_dir.exists():
                logs = sorted(log_dir.glob("*.md"), reverse=True)
                if logs:
                    print(f"\n  Latest log: {logs[0].name}\n")
                    print(logs[0].read_text()[-2000:])
                    print()
            # Loop back to prompt
            continue

        elif choice == "5":
            return False

        else:
            print("  Enter 1, 2, 3, 4, or 5.")


def _inject_feedback_and_reset(memory: Memory, task_id: str, feedback: str) -> None:
    """Append failure context to a task's input and reset it to pending for retry."""
    tasks = memory.load_tasks()
    if not tasks:
        return
    for milestone in tasks.milestones:
        for task in milestone.tasks:
            if task.id == task_id:
                task.input = task.input + f"\n\n[Retry context: {feedback[:400]}]"
                task.status = "pending"
                task.last_error = feedback[:400]
                break
    memory.save_tasks(tasks)


def _find_failing_task(tasks: TaskBoard) -> Optional[Task]:
    """Return the first task with fail_count >= MAX_TASK_RETRIES or critic_rejections >= max."""
    for milestone in tasks.milestones:
        for task in milestone.tasks:
            if task.fail_count >= MAX_TASK_RETRIES:
                return task
            if task.critic_rejections >= 3:
                return task
    return None


def _assert_planning_artifacts(project_path: Path, planning_result: AgentResult) -> None:
    """Fail fast if planning completed textually but did not create runtime artifacts."""
    plan_path = project_path / "memory" / "plan.md"
    tasks_path = project_path / "memory" / "tasks.json"

    if plan_path.exists() and tasks_path.exists():
        return

    summary = planning_result.summary or "Planning completed without writing required files."
    raise RuntimeError(
        "Initial planning did not create `memory/plan.md` and `memory/tasks.json`.\n"
        f"Planner result: {summary}\n\n"
        "The orchestrator should write these files using the write_file tool. "
        "Check that ANTHROPIC_API_KEY is set and the orchestrator agent definition is valid."
    )


def _extract_file_sections(raw_output: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []

    for line in raw_output.splitlines():
        match = re.match(r'^\*\*(.+?)\*\*\s*$', line)
        if match:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = match.group(1).strip()
            buffer = []
            continue
        if current is not None:
            buffer.append(line)

    if current is not None:
        sections[current] = "\n".join(buffer).strip()

    return sections


def _normalize_block_content(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return content


def _materialize_planning_artifacts(project_path: Path, planning_result: AgentResult) -> None:
    """Write planning artifacts from structured planner payload when present.
    Skips if the orchestrator already wrote the files via write_file tools.
    """
    if (
        (project_path / "memory" / "plan.md").exists()
        and (project_path / "memory" / "tasks.json").exists()
    ):
        return

    payload = planning_result.payload or {}
    if planning_result.status != "complete" or not payload:
        return

    raw_output = planning_result.raw_output or ""
    sections = _extract_file_sections(raw_output)

    plan_markdown = payload.get("plan_markdown")
    tasks_board = payload.get("tasks_board")
    decisions_entry = payload.get("decisions_entry")

    if isinstance(plan_markdown, str):
        if plan_markdown.startswith("memory/"):
            plan_path_candidate = project_path / plan_markdown
            if plan_path_candidate.exists():
                plan_markdown = plan_path_candidate.read_text()
            elif plan_markdown in sections:
                plan_markdown = _normalize_block_content(sections[plan_markdown])
        elif plan_markdown.strip().startswith("#") or "\n" in plan_markdown:
            plan_markdown = plan_markdown.strip()
        else:
            plan_markdown = None

    if isinstance(tasks_board, str):
        if tasks_board.startswith("memory/"):
            tasks_path_candidate = project_path / tasks_board
            if tasks_path_candidate.exists():
                try:
                    tasks_board = json.loads(tasks_path_candidate.read_text())
                except json.JSONDecodeError:
                    tasks_board = None
            elif tasks_board in sections:
                try:
                    tasks_board = json.loads(_normalize_block_content(sections[tasks_board]))
                except json.JSONDecodeError:
                    tasks_board = None
        else:
            tasks_board = None

    if isinstance(decisions_entry, str):
        if decisions_entry.startswith("memory/"):
            decisions_path_candidate = project_path / decisions_entry
            if decisions_path_candidate.exists():
                decisions_entry = decisions_path_candidate.read_text()
            elif decisions_entry in sections:
                decisions_entry = _normalize_block_content(sections[decisions_entry])
        elif not decisions_entry.strip():
            decisions_entry = None

    if not isinstance(plan_markdown, str) or not isinstance(tasks_board, dict):
        return

    plan_path = project_path / "memory" / "plan.md"
    tasks_path = project_path / "memory" / "tasks.json"
    decisions_path = project_path / "memory" / "decisions.md"

    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(plan_markdown.strip() + "\n")

    normalized_board = TaskBoard.from_dict(tasks_board)
    if not normalized_board.project:
        normalized_board.project = project_path.name

    _normalize_initial_plan_task_statuses(normalized_board)

    tasks_path.write_text(json.dumps(normalized_board.to_dict(), indent=2) + "\n")

    if isinstance(decisions_entry, str) and decisions_entry.strip():
        existing = decisions_path.read_text() if decisions_path.exists() else "# Architectural Decisions\n"
        suffix = decisions_entry.strip()
        decisions_path.write_text(existing.rstrip() + "\n\n" + suffix + "\n")


def _normalize_initial_plan_task_statuses(board: TaskBoard) -> None:
    """Normalize initial planning tasks so the loop can execute them."""
    for task in board.all_tasks():
        if task.status not in {"done", "blocked", "failed"}:
            task.status = "pending"
    board.recalculate_progress()


def _raise_missing_tasks_error(project_path: Path) -> None:
    """Raise a clearer error when planning artifacts are missing instead of looping forever."""
    plan_path = project_path / "memory" / "plan.md"
    tasks_path = project_path / "memory" / "tasks.json"
    if not plan_path.exists() or not tasks_path.exists():
        raise RuntimeError(
            "Task board was not initialized.\n"
            f"Expected files:\n- {plan_path}\n- {tasks_path}\n\n"
            "The planning model call returned, but no task files were created. "
            "This is a current runtime limitation, not a normal project-state wait."
        )


def compress_decisions_if_needed(project_path: Path, memory: Memory) -> None:
    """
    If decisions.md has grown past the threshold, summarize it with Claude
    and archive the raw log. Runs at the top of each iteration so every
    agent spawned in that iteration reads the compressed version.
    """
    if not memory.decisions_need_compression():
        return

    log.info("decisions.md exceeds threshold — compressing...")
    raw = memory.read_decisions()

    summary = call_llm(
        "",
        (
            "Summarize the following architectural decisions log into a compact, "
            "structured reference. Group entries by category (e.g. Database, Auth, "
            "API Design, Testing, Infrastructure, Libraries). For each decision keep "
            "only: the decision made, the reason, and key constraints. If a decision "
            "was superseded by a later one, keep only the final decision. "
            "Format as markdown with ## headers per category. Be concise.\n\n"
            f"Decisions log:\n{raw}"
        ),
        max_tokens=2048,
    )
    memory.archive_decisions(summary)
    log.info("decisions.md compressed and archived.")


def notify_human(project_name: str, message: str, memory: Memory, success: bool = False):
    """Print a clear notification for the human."""
    separator = "=" * 60
    status = "✅ PROJECT COMPLETE" if success else "⚠️  NEEDS YOUR ATTENTION"
    print(f"\n{separator}")
    print(f"  FrinkLoop — {status}")
    print(f"  Project: {project_name}")
    print(f"  {message}")
    print(separator)

    if success:
        summary = memory.generate_summary()
        print(f"\n{summary}\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FrinkLoop — autonomous development loop")
    parser.add_argument("--project", required=True, help="Project name (folder in projects/)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, don't execute tasks")
    parser.add_argument("--no-hitl", action="store_true", help="Skip interactive escalation; auto-skip failing tasks")
    args = parser.parse_args()

    run_loop(args.project, dry_run=args.dry_run, no_hitl=args.no_hitl)
