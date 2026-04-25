"""
core/obsidian.py — Obsidian vault sync

Exports project memory to an Obsidian vault as structured, interlinked notes.
Enable by setting OBSIDIAN_VAULT_PATH in your .env file.

Notes written under <vault>/FrinkLoop/<project-name>/:
  Dashboard.md   — task status table + progress
  Decisions.md   — current architectural decisions (compressed if large)
  Blockers.md    — active blockers
  QA Report.md   — latest QA findings

Usage (manual):
    from core.obsidian import sync_project
    sync_project(Path("projects/my-project"), Path("/path/to/vault"))

Usage (automatic):
    Set OBSIDIAN_VAULT_PATH in .env — the loop calls this after each iteration.
"""

import json
import os
from pathlib import Path
from datetime import datetime


def sync_project(project_path: Path, vault_path: Path) -> None:
    """Sync all project memory files to the Obsidian vault."""
    project_name = project_path.name
    vault_dir = vault_path / "FrinkLoop" / project_name
    vault_dir.mkdir(parents=True, exist_ok=True)

    _write_dashboard(project_path, vault_dir, project_name)
    _write_decisions(project_path, vault_dir, project_name)
    _write_blockers(project_path, vault_dir, project_name)
    _write_qa_report(project_path, vault_dir, project_name)


# ── Note writers ──────────────────────────────────────────────────────────────

def _write_dashboard(project_path: Path, vault_dir: Path, project_name: str) -> None:
    tasks_path = project_path / "memory" / "tasks.json"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [_frontmatter(f"{project_name} — Dashboard", ["frinkloop", "dashboard", project_name.lower().replace(" ", "-")], now)]
    lines.append(f"# {project_name}\n\n")
    lines.append(f"> Last synced: {now}\n\n")

    lines.append("## Notes\n\n")
    lines.append("- [[Decisions]] — architectural choices\n")
    lines.append("- [[Blockers]] — current blockers\n")
    lines.append("- [[QA Report]] — latest test results\n\n")

    if not tasks_path.exists():
        lines.append("_No tasks.json found yet._\n")
    else:
        try:
            tasks = json.loads(tasks_path.read_text())
            current_milestone = tasks.get("milestone_current", "—")
            lines.append(f"## Current milestone: {current_milestone}\n\n")

            # Progress summary
            all_tasks = [t for m in tasks.get("milestones", []) for t in m.get("tasks", [])]
            done = sum(1 for t in all_tasks if t.get("status") == "done")
            total = len(all_tasks)
            lines.append(f"**Progress:** {done}/{total} tasks complete\n\n")

            # Task table
            if all_tasks:
                lines.append("## Tasks\n\n")
                lines.append("| ID | Type | Status | Task |\n")
                lines.append("|-----|------|--------|------|\n")
                for milestone in tasks.get("milestones", []):
                    m_status = milestone.get("status", "pending")
                    lines.append(f"| **{milestone.get('id','?')}** | *milestone* | {_status_icon(m_status)} {m_status} | **{milestone.get('name','')}** |\n")
                    for task in milestone.get("tasks", []):
                        status = task.get("status", "pending")
                        task_input = task.get("input", "")[:70].replace("|", "/")
                        lines.append(
                            f"| {task['id']} | {task.get('type','')} "
                            f"| {_status_icon(status)} {status} | {task_input} |\n"
                        )
        except (json.JSONDecodeError, KeyError) as e:
            lines.append(f"_Could not parse tasks.json: {e}_\n")

    (vault_dir / "Dashboard.md").write_text("".join(lines))


def _write_decisions(project_path: Path, vault_dir: Path, project_name: str) -> None:
    decisions_path = project_path / "memory" / "decisions.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    body = decisions_path.read_text() if decisions_path.exists() else "_No decisions logged yet._\n"
    header = _frontmatter(f"{project_name} — Decisions", ["frinkloop", "decisions", project_name.lower().replace(" ", "-")], now)
    header += f"> Last synced: {now} | [[Dashboard]]\n\n"

    (vault_dir / "Decisions.md").write_text(header + body)


def _write_blockers(project_path: Path, vault_dir: Path, project_name: str) -> None:
    blockers_path = project_path / "memory" / "blockers.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    body = blockers_path.read_text() if blockers_path.exists() else "_No blockers._\n"
    header = _frontmatter(f"{project_name} — Blockers", ["frinkloop", "blockers", project_name.lower().replace(" ", "-")], now)
    header += f"> Last synced: {now} | [[Dashboard]]\n\n"

    (vault_dir / "Blockers.md").write_text(header + body)


def _write_qa_report(project_path: Path, vault_dir: Path, project_name: str) -> None:
    qa_path = project_path / "memory" / "qa_report.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    body = qa_path.read_text() if qa_path.exists() else "_No QA report yet._\n"
    header = _frontmatter(f"{project_name} — QA Report", ["frinkloop", "qa", project_name.lower().replace(" ", "-")], now)
    header += f"> Last synced: {now} | [[Dashboard]]\n\n"

    (vault_dir / "QA Report.md").write_text(header + body)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _frontmatter(title: str, tags: list, updated: str) -> str:
    tag_lines = "\n".join(f"  - {t}" for t in tags)
    return f"---\ntitle: \"{title}\"\ntags:\n{tag_lines}\nupdated: \"{updated}\"\n---\n\n"


def _status_icon(status: str) -> str:
    return {"done": "✅", "in_progress": "🔄", "failed": "❌", "blocked": "🚫"}.get(status, "⏳")


def vault_path_from_env() -> Path | None:
    """Return the configured Obsidian vault path, or None if not set."""
    raw = os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.exists():
        return None
    return path
