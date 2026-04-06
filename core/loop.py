"""
core/loop.py — The autonomous iteration engine

This is the heart of the Agent OS. It reads tasks.json, assigns agents,
executes work, and loops until the project is done or escalation triggers.

Usage:
    python core/loop.py --project <project-name>
    python core/loop.py --project firecrawl-clone --dry-run
"""

import os
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import anthropic

from core.spawn import spawn_agent
from core.memory import Memory
from core.escalation import check_escalation
from core.obsidian import sync_project, vault_path_from_env
from core.github import commit_task, push_to_remote, open_issue_for_blocker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("agent-os")


# ─── Configuration ────────────────────────────────────────────────────────────

MAX_TASK_RETRIES = 5          # escalate if same task fails this many times
MAX_LOOP_ITERATIONS = 200     # hard stop to prevent infinite loops
LOOP_SLEEP_SECONDS = 2        # pause between iterations

AGENT_TASK_MAP = {
    "research":  "researcher",
    "code":      "developer",
    "test":      "qa",
    "review":    "critic",
    "plan":      "orchestrator",
}


# ─── Main Loop ────────────────────────────────────────────────────────────────

def run_loop(project_name: str, dry_run: bool = False) -> None:
    """Main autonomous loop. Runs until project is done or escalation triggers."""

    project_path = Path("projects") / project_name
    memory = Memory(project_path)

    log.info(f"Starting Agent OS loop for project: {project_name}")
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
        spawn_agent(
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

    # ── Main Loop ─────────────────────────────────────────────────────────────
    for iteration in range(MAX_LOOP_ITERATIONS):
        log.info(f"─── Iteration {iteration + 1} ───────────────────────────────")

        # Compress decisions.md if it has grown too large
        compress_decisions_if_needed(project_path, memory)

        tasks = memory.load_tasks()
        if not tasks:
            log.info("No tasks found. Waiting for Orchestrator to generate tasks...")
            time.sleep(LOOP_SLEEP_SECONDS)
            continue

        # Check escalation conditions
        escalation = check_escalation(tasks, memory)
        if escalation:
            log.warning(f"ESCALATION TRIGGERED: {escalation}")
            should_continue = handle_escalation_interactively(escalation, tasks, memory, project_path, dry_run)
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
        log.info(f"Executing task {task['id']}: [{task['type']}] {task['input'][:80]}...")
        memory.update_task_status(task["id"], "in_progress")

        try:
            agent_name = AGENT_TASK_MAP.get(task["type"], task.get("agent", "developer"))
            result = spawn_agent(
                agent=agent_name,
                task=task,
                project_path=project_path,
                dry_run=dry_run,
            )
            memory.update_task_status(task["id"], "done", result=result)
            log.info(f"✓ Task {task['id']} completed by {agent_name}")

            # Git commit for this task
            commit_task(project_path, task)

            # Push to GitHub after each milestone completes
            tasks_now = memory.load_tasks() or {}
            current_m_id = tasks_now.get("milestone_current")
            current_m = next(
                (m for m in tasks_now.get("milestones", []) if m.get("id") == current_m_id), None
            )
            if current_m and current_m.get("status") == "done":
                log.info(f"Milestone {current_m_id} complete — pushing to GitHub")
                push_to_remote(project_path)

            # Obsidian sync
            vault = vault_path_from_env()
            if vault:
                try:
                    sync_project(project_path, vault)
                    log.info(f"Obsidian vault synced → {vault}/DevOS/{project_path.name}/")
                except Exception as e:
                    log.warning(f"Obsidian sync failed (non-fatal): {e}")

        except Exception as e:
            log.error(f"✗ Task {task['id']} failed: {e}")
            fail_count = memory.increment_fail_count(task["id"])
            memory.update_task_status(task["id"], "failed", error=str(e))

            if fail_count >= MAX_TASK_RETRIES:
                log.warning(f"Task {task['id']} has failed {fail_count} times — escalating")
                blocker_reason = f"Task failed {fail_count} times. Last error: {e}"
                memory.write_blocker(task["id"], blocker_reason)
                issue_url = open_issue_for_blocker(project_path, task["id"], blocker_reason)
                if issue_url:
                    log.info(f"GitHub issue opened: {issue_url}")

        time.sleep(LOOP_SLEEP_SECONDS)

    log.error(f"Hit maximum iterations ({MAX_LOOP_ITERATIONS}) — something may be stuck.")
    notify_human(project_name, f"Loop hit max iterations ({MAX_LOOP_ITERATIONS}). Check memory/blockers.md", memory)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_next_task(tasks: dict) -> Optional[dict]:
    """Find the next task that is ready to run (pending + dependencies met)."""
    all_done_ids = {
        t["id"] for milestone in tasks.get("milestones", [])
        for t in milestone.get("tasks", [])
        if t.get("status") == "done"
    }

    for milestone in tasks.get("milestones", []):
        if milestone.get("status") == "done":
            continue
        for task in milestone.get("tasks", []):
            if task.get("status") not in ("pending", None):
                continue
            deps = task.get("depends_on", [])
            if all(dep in all_done_ids for dep in deps):
                return task

    return None


def all_milestones_complete(tasks: dict) -> bool:
    """Return True only when every milestone and every task is done."""
    for milestone in tasks.get("milestones", []):
        if milestone.get("status") != "done":
            return False
        for task in milestone.get("tasks", []):
            if task.get("status") != "done":
                return False
    return True


def handle_blocked_tasks(tasks: dict, memory: Memory, project_path: Path, dry_run: bool):
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
    tasks: dict,
    memory: Memory,
    project_path: Path,
    dry_run: bool,
) -> bool:
    """
    Present escalation options to the user and act on their choice.
    Returns True if the loop should continue, False if it should stop.
    """
    separator = "═" * 60
    print(f"\n{separator}")
    print("  Agent OS — NEEDS YOUR ATTENTION")
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
                failing_task["input"] = failing_task["input"] + f"\n\nHuman context: {context}"
                failing_task["status"] = "pending"
                failing_task["fail_count"] = 0
                failing_task["last_error"] = ""
                memory.save_tasks(tasks)
                memory.clear_blocker(failing_task["id"])
                memory.log_decision(
                    f"Human unblocked task {failing_task['id']}",
                    f"User added context: {context[:200]}",
                )
                log.info(f"Task {failing_task['id']} reset with human context — continuing loop")
            return True

        elif choice == "2" and failing_task:
            failing_task["status"] = "done"
            failing_task["result_summary"] = "Skipped by human decision"
            memory.save_tasks(tasks)
            memory.clear_blocker(failing_task["id"])
            memory.log_decision(
                f"Skipped task {failing_task['id']}",
                "Human chose to skip this task during escalation",
            )
            log.info(f"Task {failing_task['id']} skipped — continuing loop")
            return True

        elif choice == "3" and failing_task:
            try:
                approach = input("  Describe the new approach: ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if approach:
                failing_task["input"] = approach
                failing_task["status"] = "pending"
                failing_task["fail_count"] = 0
                failing_task["last_error"] = ""
                memory.save_tasks(tasks)
                memory.clear_blocker(failing_task["id"])
                memory.log_decision(
                    f"Replaced task {failing_task['id']} with new approach",
                    f"Human replaced approach: {approach[:200]}",
                )
                log.info(f"Task {failing_task['id']} replaced — continuing loop")
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


def _find_failing_task(tasks: dict) -> Optional[dict]:
    """Return the first task with fail_count >= MAX_TASK_RETRIES or critic_rejections >= max."""
    for milestone in tasks.get("milestones", []):
        for task in milestone.get("tasks", []):
            if task.get("fail_count", 0) >= MAX_TASK_RETRIES:
                return task
            if task.get("critic_rejections", 0) >= 3:
                return task
    return None


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

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": (
                "Summarize the following architectural decisions log into a compact, "
                "structured reference. Group entries by category (e.g. Database, Auth, "
                "API Design, Testing, Infrastructure, Libraries). For each decision keep "
                "only: the decision made, the reason, and key constraints. If a decision "
                "was superseded by a later one, keep only the final decision. "
                "Format as markdown with ## headers per category. Be concise.\n\n"
                f"Decisions log:\n{raw}"
            ),
        }],
    )

    summary = response.content[0].text
    memory.archive_decisions(summary)
    log.info("decisions.md compressed and archived.")


def notify_human(project_name: str, message: str, memory: Memory, success: bool = False):
    """Print a clear notification for the human."""
    separator = "=" * 60
    status = "✅ PROJECT COMPLETE" if success else "⚠️  NEEDS YOUR ATTENTION"
    print(f"\n{separator}")
    print(f"  Agent OS — {status}")
    print(f"  Project: {project_name}")
    print(f"  {message}")
    print(separator)

    if success:
        summary = memory.generate_summary()
        print(f"\n{summary}\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent OS — autonomous development loop")
    parser.add_argument("--project", required=True, help="Project name (folder in projects/)")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, don't execute tasks")
    args = parser.parse_args()

    run_loop(args.project, dry_run=args.dry_run)
