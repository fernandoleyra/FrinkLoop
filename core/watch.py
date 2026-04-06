"""
core/watch.py — Live dashboard for a running agent loop

Polls tasks.json and agent_logs/ every 2 seconds and renders a
terminal dashboard. Works with any terminal width ≥ 60 columns.

Keys (when terminal supports raw input):
  d — print current decisions.md inline
  b — print current blockers.md inline
  q — quit
"""

import json
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

REFRESH_SECONDS = 2


def run_watch(project_name: str) -> None:
    project_path = ROOT / "projects" / project_name
    if not project_path.exists():
        print(f"Project not found: {project_path}")
        sys.exit(1)

    memory_path = project_path / "memory"

    # Start key-listener thread (non-blocking)
    key_queue: list[str] = []
    _start_key_listener(key_queue)

    print(f"\n  Watching '{project_name}' — press [d] decisions  [b] blockers  [q] quit\n")

    try:
        while True:
            # Handle key presses
            if key_queue:
                key = key_queue.pop(0)
                if key == "q":
                    print("\n  Stopped watching.\n")
                    break
                elif key == "d":
                    _print_file(memory_path / "decisions.md", "Architectural Decisions")
                elif key == "b":
                    _print_file(memory_path / "blockers.md", "Blockers")
                continue

            # Render dashboard
            _render(project_name, project_path, memory_path)
            time.sleep(REFRESH_SECONDS)

    except KeyboardInterrupt:
        print("\n  Stopped watching.\n")


def _render(project_name: str, project_path: Path, memory_path: Path) -> None:
    tasks_path  = memory_path / "tasks.json"
    state_path  = memory_path / "state.json"
    log_dir     = memory_path / "agent_logs"

    now = datetime.now().strftime("%H:%M:%S")
    width = min(os.get_terminal_size().columns, 80) if hasattr(os, "get_terminal_size") else 70

    lines = []
    lines.append(_divider(width))
    lines.append(f"  Agent OS — {project_name:<30} {now:>10}  ")
    lines.append(_divider(width))

    # State
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            phase     = state.get("phase", "—")
            milestone = state.get("milestone_current", "—")
            lines.append(f"  Phase: {phase}   Milestone: {milestone}")
        except Exception:
            pass

    lines.append("")

    # Milestones + task table
    if tasks_path.exists():
        try:
            data = json.loads(tasks_path.read_text())
            milestones = data.get("milestones", [])
            current_task = None

            for m in milestones:
                tasks = m.get("tasks", [])
                done  = sum(1 for t in tasks if t.get("status") == "done")
                total = len(tasks)
                bar   = _bar(done, total, 12)
                m_status = m.get("status", "pending")
                icon = "✅" if m_status == "done" else "🔄" if any(t.get("status") == "in_progress" for t in tasks) else "⏳"
                lines.append(f"  {bar}  {icon}  {m.get('id','?')} {m.get('name','')[:32]:<32} {done}/{total}")

                for t in tasks:
                    if t.get("status") == "in_progress":
                        current_task = t

            lines.append("")

            # Current task detail
            if current_task:
                lines.append(f"  Running: [{current_task.get('type','')}] {current_task.get('id','')}  agent: {current_task.get('agent','')}")
                lines.append(f"  Task:    {current_task.get('input','')[:width - 12]}")
                fails = current_task.get("fail_count", 0)
                if fails:
                    lines.append(f"  Fails:   {fails}")
            else:
                # Check if all done
                all_tasks = [t for m in milestones for t in m.get("tasks", [])]
                if all_tasks and all(t.get("status") == "done" for t in all_tasks):
                    lines.append("  ✅ All tasks complete")
                else:
                    lines.append("  ⏳ Waiting for next task...")

        except Exception as e:
            lines.append(f"  Could not parse tasks.json: {e}")
    else:
        lines.append("  No tasks.json yet — loop may still be initializing")

    lines.append("")

    # Recent agent log entries (last 4)
    if log_dir.exists():
        logs = sorted(log_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:4]
        if logs:
            lines.append("  Recent:")
            for lf in reversed(logs):
                parts = lf.stem.split("_")
                # format: YYYYMMDD_HHMMSS_agent_taskid
                if len(parts) >= 4:
                    ts    = parts[1][:4]  # HHMM
                    agent = parts[2]
                    tid   = parts[3]
                    lines.append(f"    {ts[:2]}:{ts[2:]}  {agent:<12}  {tid}")

    lines.append("")
    lines.append(f"  [d] decisions  [b] blockers  [q] quit")
    lines.append(_divider(width))

    # Move cursor up and overwrite
    # Use ANSI: clear from cursor to end of screen, then print
    num_lines = len(lines)
    sys.stdout.write(f"\033[{num_lines + 1}A")  # move up
    sys.stdout.write("\033[J")                   # clear to end
    print("\n".join(lines))
    sys.stdout.flush()


def _divider(width: int) -> str:
    return "  " + "─" * (width - 2)


def _bar(done: int, total: int, width: int = 10) -> str:
    if total == 0:
        return "░" * width
    filled = round((done / total) * width)
    return "█" * filled + "░" * (width - filled)


def _print_file(path: Path, title: str) -> None:
    print(f"\n  ── {title} ─────────────────────────────")
    if path.exists():
        content = path.read_text().strip()
        if content:
            for line in content.splitlines():
                print(f"  {line}")
        else:
            print("  (empty)")
    else:
        print("  (file not found)")
    print()


def _start_key_listener(key_queue: list) -> None:
    """Start a background thread that reads single keypresses and adds to queue."""
    def _listen():
        try:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    ch = sys.stdin.read(1)
                    if ch in ("q", "d", "b"):
                        key_queue.append(ch)
                    if ch == "q":
                        break
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            # Non-TTY environment (piped input, Windows) — key listening disabled
            pass

    t = threading.Thread(target=_listen, daemon=True)
    t.start()
