"""
core/memory.py — Shared memory system for all agents

The memory directory is the message bus. Agents communicate by reading
and writing to well-known files rather than calling each other directly.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# decisions.md is compressed when it exceeds this character count (~1k tokens)
DECISIONS_COMPRESS_THRESHOLD = 4000


class Memory:
    """Interface to the project's shared memory directory."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.memory_path = project_path / "memory"
        self.memory_path.mkdir(parents=True, exist_ok=True)
        (project_path / "src").mkdir(exist_ok=True)
        (project_path / "tests").mkdir(exist_ok=True)
        (self.memory_path / "research").mkdir(exist_ok=True)
        (self.memory_path / "agent_logs").mkdir(exist_ok=True)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def load_tasks(self) -> Optional[dict]:
        """Load tasks.json. Returns None if it doesn't exist yet."""
        tasks_path = self.memory_path / "tasks.json"
        if not tasks_path.exists():
            return None
        return json.loads(tasks_path.read_text())

    def save_tasks(self, tasks: dict) -> None:
        """Save tasks.json atomically."""
        tasks_path = self.memory_path / "tasks.json"
        tasks_path.write_text(json.dumps(tasks, indent=2))

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update a single task's status in tasks.json."""
        tasks = self.load_tasks()
        if not tasks:
            return

        for milestone in tasks.get("milestones", []):
            for task in milestone.get("tasks", []):
                if task["id"] == task_id:
                    task["status"] = status
                    task["updated_at"] = datetime.now().isoformat()
                    if result:
                        task["result_summary"] = result[:500]
                    if error:
                        task["last_error"] = error[:500]
                    break

            # Check if milestone is now complete
            all_done = all(t.get("status") == "done" for t in milestone.get("tasks", []))
            if all_done and milestone.get("tasks"):
                milestone["status"] = "done"

        self.save_tasks(tasks)

    def increment_fail_count(self, task_id: str) -> int:
        """Increment and return the fail count for a task."""
        tasks = self.load_tasks()
        if not tasks:
            return 1

        for milestone in tasks.get("milestones", []):
            for task in milestone.get("tasks", []):
                if task["id"] == task_id:
                    count = task.get("fail_count", 0) + 1
                    task["fail_count"] = count
                    self.save_tasks(tasks)
                    return count
        return 1

    # ── Blockers ──────────────────────────────────────────────────────────────

    def write_blocker(self, task_id: str, reason: str) -> None:
        """Write a blocker to memory/blockers.md."""
        blockers_path = self.memory_path / "blockers.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n## [{task_id}] — {timestamp}\n{reason}\n"

        existing = blockers_path.read_text() if blockers_path.exists() else "# Blockers\n"
        blockers_path.write_text(existing + entry)

    def read_blockers(self) -> str:
        """Read all current blockers."""
        blockers_path = self.memory_path / "blockers.md"
        return blockers_path.read_text() if blockers_path.exists() else ""

    def clear_blocker(self, task_id: str) -> None:
        """Mark a blocker as resolved."""
        blockers_path = self.memory_path / "blockers.md"
        if not blockers_path.exists():
            return
        content = blockers_path.read_text()
        content = content.replace(f"## [{task_id}]", f"## [RESOLVED: {task_id}]")
        blockers_path.write_text(content)

    # ── Decisions ─────────────────────────────────────────────────────────────

    def log_decision(self, decision: str, reason: str, alternatives: str = "") -> None:
        """Log an architectural decision to decisions.md."""
        decisions_path = self.memory_path / "decisions.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        entry = f"\n## {timestamp}\n**Decision:** {decision}\n**Reason:** {reason}\n"
        if alternatives:
            entry += f"**Alternatives:** {alternatives}\n"

        existing = decisions_path.read_text() if decisions_path.exists() else "# Architectural Decisions\n"
        decisions_path.write_text(existing + entry)

    # ── Decisions compression ─────────────────────────────────────────────────

    def decisions_need_compression(self) -> bool:
        """Return True if decisions.md has grown beyond the compression threshold."""
        decisions_path = self.memory_path / "decisions.md"
        if not decisions_path.exists():
            return False
        return len(decisions_path.read_text()) > DECISIONS_COMPRESS_THRESHOLD

    def read_decisions(self) -> str:
        """Read current decisions.md content."""
        decisions_path = self.memory_path / "decisions.md"
        return decisions_path.read_text() if decisions_path.exists() else ""

    def archive_decisions(self, summary: str) -> None:
        """
        Archive the full decisions.md to memory/archive/ and replace it with
        a structured summary. Called after Claude compresses the file.
        """
        decisions_path = self.memory_path / "decisions.md"
        archive_dir = self.memory_path / "archive"
        archive_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = archive_dir / f"decisions_{timestamp}.md"

        if decisions_path.exists():
            archive_path.write_text(decisions_path.read_text())

        header = (
            f"# Architectural Decisions\n"
            f"_Compressed on {datetime.now().strftime('%Y-%m-%d %H:%M')} — "
            f"full history in memory/archive/decisions_{timestamp}.md_\n\n"
        )
        decisions_path.write_text(header + summary)

    # ── Summary ───────────────────────────────────────────────────────────────

    def generate_summary(self) -> str:
        """Generate a completion summary for the human."""
        tasks = self.load_tasks() or {}
        total = sum(len(m.get("tasks", [])) for m in tasks.get("milestones", []))
        done = sum(
            1 for m in tasks.get("milestones", [])
            for t in m.get("tasks", [])
            if t.get("status") == "done"
        )

        src_tree = self._get_src_summary()
        decisions_path = self.memory_path / "decisions.md"
        decisions = decisions_path.read_text() if decisions_path.exists() else "None logged."

        return f"""
## Project Complete

**Tasks:** {done}/{total} completed
**Project folder:** {self.project_path}

## Files Created
{src_tree}

## Key Decisions Made
{decisions[:1000]}

## Next Steps
- Run: `cd {self.project_path}/src && python main.py` (or check README)
- Review: `{self.project_path}/memory/decisions.md` for architectural notes
- Tests: `cd {self.project_path} && pytest tests/`
""".strip()

    def _get_src_summary(self) -> str:
        src_path = self.project_path / "src"
        if not src_path.exists():
            return "No src/ files found."
        files = list(src_path.rglob("*.py")) + list(src_path.rglob("*.ts"))
        return "\n".join(f"  - {f.relative_to(self.project_path)}" for f in files[:20])
