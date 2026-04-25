"""
core/handoff.py — Cross-device project continuity

handoff: snapshot current state into HANDOFF.md, git-commit, optionally push
wake:    read HANDOFF.md, validate env, reset interrupted tasks, start loop
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ── Handoff ───────────────────────────────────────────────────────────────────

def create_handoff(project_name: str, push: bool = False) -> None:
    project_path = ROOT / "projects" / project_name
    memory_path = project_path / "memory"

    if not project_path.exists():
        print(f"Project not found: {project_path}")
        sys.exit(1)

    print(f"\n  Creating handoff snapshot for '{project_name}'...\n")

    # Load current state
    tasks_data = _load_json(memory_path / "tasks.json") or {}
    decisions = _read_file(memory_path / "decisions.md")
    blockers  = _read_file(memory_path / "blockers.md")

    # Identify in-progress and last completed task
    all_tasks = [t for m in tasks_data.get("milestones", []) for t in m.get("tasks", [])]
    in_progress = [t for t in all_tasks if t.get("status") == "in_progress"]
    done_tasks  = [t for t in all_tasks if t.get("status") == "done"]
    last_done   = done_tasks[-1] if done_tasks else None

    # Current milestone
    milestone_id = tasks_data.get("milestone_current", "—")
    milestones = tasks_data.get("milestones", [])
    current_m = next((m for m in milestones if m.get("id") == milestone_id), None)

    # Progress counts
    total = len(all_tasks)
    done_count = len(done_tasks)

    # Recent git changes
    changed_files = _git_changed_files(project_path)

    # Machine info
    import platform
    machine = platform.node() or platform.system()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Build HANDOFF.md
    in_progress_section = ""
    if in_progress:
        t = in_progress[0]
        in_progress_section = (
            f"- **In-progress task**: {t['id']} — {t.get('input','')[:80]}\n"
            f"  - This task was interrupted mid-run. `wake` will reset it to pending and restart it cleanly.\n"
        )
    else:
        in_progress_section = "- No task was in-progress at snapshot time.\n"

    last_done_section = ""
    if last_done:
        last_done_section = f"- **Last completed task**: {last_done['id']} — {last_done.get('input','')[:80]}\n"

    milestone_section = ""
    if current_m:
        m_tasks = current_m.get("tasks", [])
        m_done  = sum(1 for t in m_tasks if t.get("status") == "done")
        milestone_section = f"- **Milestone**: {milestone_id} — {current_m.get('name','')} ({m_done}/{len(m_tasks)} tasks done)\n"

    files_section = "\n".join(f"- {f}" for f in changed_files[:20]) if changed_files else "- (no uncommitted changes)"

    blockers_section = blockers.strip() if blockers.strip() and "(none)" not in blockers else "_No active blockers._"

    handoff_doc = f"""# Handoff — {project_name}
_Created: {timestamp} on {machine}_

---

## State at snapshot

- **Project**: {project_name}
- **Progress**: {done_count}/{total} tasks complete
{milestone_section}{last_done_section}{in_progress_section}
## To resume on another machine

```bash
# 1. Clone the repo (or pull if already cloned)
git clone <your-repo-url>
cd "$(basename <your-repo-url> .git)"

# 2. Set up environment
cp .env.example .env
# Add your model provider settings (and GITHUB_TOKEN, OBSIDIAN_VAULT_PATH if needed)
python3 frinkloop.py init

# 3. Wake the project
python3 frinkloop.py wake {project_name}
```

---

## Current architecture decisions

{decisions.strip() if decisions.strip() else '_No decisions logged yet._'}

---

## Files changed since last commit

{files_section}

---

## Active blockers

{blockers_section}
"""

    # Write HANDOFF.md to project root
    handoff_path = project_path / "HANDOFF.md"
    handoff_path.write_text(handoff_doc)
    print(f"  ✓ HANDOFF.md written")

    # Sync to Obsidian if configured
    vault_raw = os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
    if vault_raw:
        vault = Path(vault_raw).expanduser()
        if vault.exists():
            try:
                from core.obsidian import sync_project
                sync_project(project_path, vault)
                print(f"  ✓ Obsidian vault synced")
            except Exception as e:
                print(f"  ⚠ Obsidian sync failed: {e}")

    # Git commit
    committed = _git_commit_handoff(project_path, project_name, timestamp)
    if committed:
        print(f"  ✓ Git commit: handoff({project_name})")

    # Push if requested
    if push and _has_git_remote(project_path):
        try:
            subprocess.run(["git", "push"], cwd=project_path, check=True, capture_output=True)
            print(f"  ✓ Pushed to remote")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠ Push failed: {e.stderr.decode()[:100]}")

    print()
    print(f"  Handoff complete. Share HANDOFF.md or push the repo to resume on another machine.")
    print(f"  Resume command:  python3 frinkloop.py wake {project_name}\n")


# ── Wake ─────────────────────────────────────────────────────────────────────

def wake_project(project_name: str, dry_run: bool = False) -> None:
    project_path = ROOT / "projects" / project_name
    memory_path  = project_path / "memory"
    handoff_path = project_path / "HANDOFF.md"

    if not project_path.exists():
        print(f"Project not found: {project_path}")
        print(f"Make sure you've cloned the repo and the project is in projects/{project_name}/")
        sys.exit(1)

    print(f"\n  Waking project '{project_name}'...\n")

    # Show handoff summary
    if handoff_path.exists():
        _print_handoff_summary(handoff_path)
    else:
        print("  No HANDOFF.md found — starting fresh from current tasks.json state.\n")

    # Validate environment
    issues = _validate_env()
    if issues:
        print("  Environment issues found:")
        for issue in issues:
            print(f"    ✗ {issue}")
        print("\n  Fix these before resuming. Run: python3 frinkloop.py init")
        sys.exit(1)
    print("  ✓ Environment looks good\n")

    # Reset any in_progress tasks back to pending
    tasks_path = memory_path / "tasks.json"
    if tasks_path.exists():
        tasks_data = _load_json(tasks_path)
        reset_count = 0
        for m in tasks_data.get("milestones", []):
            for t in m.get("tasks", []):
                if t.get("status") == "in_progress":
                    t["status"] = "pending"
                    t["updated_at"] = datetime.utcnow().isoformat()
                    reset_count += 1
        if reset_count:
            tasks_path.write_text(json.dumps(tasks_data, indent=2))
            print(f"  ✓ Reset {reset_count} interrupted task(s) to pending")

    # Confirm resume
    try:
        answer = input("  Resume loop now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)

    if answer and not answer.startswith("y"):
        print("  Aborted. Run when ready:  python3 frinkloop.py run " + project_name)
        return

    print()
    from core.loop import run_loop
    run_loop(project_name, dry_run=dry_run)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _read_file(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def _git_changed_files(project_path: Path) -> list:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=project_path, capture_output=True, text=True, timeout=5,
        )
        files = [f for f in result.stdout.splitlines() if f]
        if not files:
            # Also check untracked
            result2 = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=project_path, capture_output=True, text=True, timeout=5,
            )
            files = [f for f in result2.stdout.splitlines() if f]
        return files
    except Exception:
        return []


def _git_commit_handoff(project_path: Path, project_name: str, timestamp: str) -> bool:
    try:
        subprocess.run(["git", "add", "HANDOFF.md"], cwd=project_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"handoff({project_name}): snapshot at {timestamp}"],
            cwd=project_path, check=True, capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _has_git_remote(project_path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "remote"], cwd=project_path, capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _print_handoff_summary(handoff_path: Path) -> None:
    content = handoff_path.read_text()
    # Extract just the State section
    lines = content.splitlines()
    in_state = False
    for line in lines:
        if line.startswith("## State at snapshot"):
            in_state = True
            print(f"  Last handoff:")
            continue
        if in_state:
            if line.startswith("## "):
                break
            if line.strip():
                print(f"  {line}")
    print()


def _validate_env() -> list:
    from core.llm import validate_llm_env

    return validate_llm_env()
