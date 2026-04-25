#!/usr/bin/env python3
"""
frinkloop — The FrinkLoop command-line interface

Commands:
  init              First-time setup wizard
  new  <name>       Create a new project (interactive brief builder)
  run  <name>       Start or resume the agent loop
  watch <name>      Live dashboard for a running loop
  handoff <name>    Snapshot current state for cross-device continuity
  wake  <name>      Resume a project from a handoff snapshot
  status [name]     Print project status summary
  help              Show this message

Usage:
  python3 frinkloop.py init
  python3 frinkloop.py new my-app
  python3 frinkloop.py run my-app
  python3 frinkloop.py watch my-app
  python3 frinkloop.py handoff my-app
  python3 frinkloop.py wake my-app
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

from core.llm import validate_llm_env, verify_llm_connection

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="frinkloop",
        description="FrinkLoop — autonomous development system",
        add_help=False,
    )
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("project", nargs="?", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-hitl", action="store_true", help="Skip interactive escalation; auto-skip failing tasks")
    parser.add_argument("--push", action="store_true", help="Push to GitHub after handoff")
    args = parser.parse_args()

    commands = {
        "init":    cmd_init,
        "new":     cmd_new,
        "run":     cmd_run,
        "watch":   cmd_watch,
        "handoff": cmd_handoff,
        "wake":    cmd_wake,
        "status":  cmd_status,
        "help":    cmd_help,
    }

    fn = commands.get(args.command)
    if fn is None:
        print(f"Unknown command: {args.command}")
        cmd_help()
        sys.exit(1)

    fn(args)


# ── Feature 1: init ───────────────────────────────────────────────────────────

def cmd_init(args=None):
    """Interactive first-time setup wizard."""
    _banner("FrinkLoop — Setup")

    env_path = ROOT / ".env"
    existing = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()

    print("This sets up your .env file. Press Enter to keep existing values.\n")

    current_provider = existing.get("MODEL_PROVIDER", os.getenv("MODEL_PROVIDER", "anthropic"))
    provider = _prompt(
        f"Model provider [anthropic/openrouter/groq/ollama/gemini] [{current_provider}]",
        default=current_provider,
    ).strip().lower()
    if provider not in {"anthropic", "openrouter", "groq", "ollama", "gemini"}:
        print(f"Unsupported provider: {provider}")
        sys.exit(1)

    model_defaults = {
        "anthropic": "claude-sonnet-4-20250514",
        "openrouter": "anthropic/claude-3.5-sonnet",
        "groq": "llama-3.3-70b-versatile",
        "ollama": "llama3.1",
        "gemini": "gemini-2.0-flash",
    }
    current_model = existing.get("MODEL_NAME", os.getenv("MODEL_NAME", model_defaults[provider]))
    model_name = _prompt(f"Model name [{current_model}]", default=current_model).strip()

    api_env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    api_key = ""
    if provider in api_env_map:
        api_env = api_env_map[provider]
        current_key = existing.get(api_env, os.getenv(api_env, ""))
        if current_key:
            masked = current_key[:8] + "..." + current_key[-4:]
            api_key = _prompt(f"{api_env} [{masked}]", default=current_key, secret=True)
        else:
            api_key = _prompt(api_env, required=True, secret=True)

    ollama_base_url = ""
    if provider == "ollama":
        current_base_url = existing.get("OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        ollama_base_url = _prompt(f"Ollama base URL [{current_base_url}]", default=current_base_url).strip()

    # GitHub token (optional)
    current_gh = existing.get("GITHUB_TOKEN", "")
    if current_gh:
        gh_token = _prompt("GitHub personal access token [already set, Enter to keep]", default=current_gh, secret=True)
    else:
        gh_token = _prompt("GitHub personal access token (leave blank to skip)", default="", secret=True)

    # Obsidian vault
    current_obs = existing.get("OBSIDIAN_VAULT_PATH", "")
    obsidian = _prompt(
        f"Obsidian vault path{f' [{current_obs}]' if current_obs else ' (leave blank to skip)'}",
        default=current_obs,
    )
    if obsidian:
        obsidian = str(Path(obsidian).expanduser())

    # Default stack
    current_stack = existing.get("DEFAULT_STACK", "TypeScript")
    default_stack = _prompt(f"Default stack when BRIEF doesn't specify [{current_stack}]", default=current_stack)

    # Write .env
    lines = [
        f"MODEL_PROVIDER={provider}",
        f"MODEL_NAME={model_name}",
        f"DEFAULT_STACK={default_stack}",
    ]
    if api_key:
        lines.append(f"{api_env_map[provider]}={api_key}")
    if ollama_base_url:
        lines.append(f"OLLAMA_BASE_URL={ollama_base_url}")
    if gh_token:
        lines.append(f"GITHUB_TOKEN={gh_token}")
    if obsidian:
        lines.append(f"OBSIDIAN_VAULT_PATH={obsidian}")

    env_path.write_text("\n".join(lines) + "\n")

    print()
    print("  ✓ .env written")

    ok, message = verify_llm_connection()
    if ok:
        print(f"  ✓ {message}")
    else:
        print(f"  ⚠ Could not verify model provider connection — {message}")

    # Verify GitHub token
    if gh_token:
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.github.com/user",
                headers={"Authorization": f"token {gh_token}", "User-Agent": "frinkloop"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                import json
                user = json.loads(r.read())["login"]
            print(f"  ✓ GitHub connected as @{user}")
        except Exception:
            print("  ⚠ Could not verify GitHub token — check it has repo scope")

    # Verify Obsidian vault
    if obsidian:
        if Path(obsidian).exists():
            print(f"  ✓ Obsidian vault linked: {obsidian}")
        else:
            print(f"  ⚠ Obsidian vault path not found: {obsidian}")

    print()
    print("  Ready. Next step:")
    print("    python3 frinkloop.py new <project-name>\n")


# ── Feature 6: new (brief builder) ───────────────────────────────────────────

def cmd_new(args):
    """Interactive project creation with LLM-powered brief builder."""
    project_name = args.project
    if not project_name:
        project_name = _prompt("Project name").strip().replace(" ", "-")
    if not project_name:
        print("Project name required.")
        sys.exit(1)

    project_path = ROOT / "projects" / project_name
    if project_path.exists():
        print(f"Project '{project_name}' already exists at {project_path}")
        sys.exit(1)

    _banner(f"New Project — {project_name}")

    # --- LLM-powered brief generator ---
    from core.brief_generator import generate_brief_interactive
    brief, answers = generate_brief_interactive(project_name, _prompt, _prompt_multiline, _prompt_list, _confirm)

    if not brief:
        print("\n⚠ Brief generation skipped. You can create the project manually.")
        sys.exit(1)

    # GitHub repo?
    gh_token = os.getenv("GITHUB_TOKEN", "")
    github_repo_url = ""
    if gh_token:
        create_repo = _confirm(f"\nCreate GitHub repo github.com/<you>/{project_name}?")
        if create_repo:
            github_repo_url = _create_github_repo(project_name, gh_token, brief[:100])

    # Select the best-matching starter template
    import shutil
    _TEMPLATE_MAP = {
        "CLI tool (command-line utility)": "cli-tool",
        "REST API / Backend service":      "api",
        "Web app (frontend)":              "web-app",
        "scraper":                         "scraper",
    }
    raw_idea = answers.get("raw_idea", "")
    template_name = _TEMPLATE_MAP.get(raw_idea, "_template")
    template_path = ROOT / "templates" / template_name
    if not template_path.exists():
        template_path = ROOT / "projects" / "_template"
    shutil.copytree(str(template_path), str(project_path))

    # Write BRIEF.md
    (project_path / "BRIEF.md").write_text(brief + "\n")

    # Init git and optionally link remote
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=project_path, check=True)
    subprocess.run(["git", "add", "."], cwd=project_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", f"chore: initialize {project_name} from FrinkLoop template"],
        cwd=project_path, check=True,
    )
    if github_repo_url:
        subprocess.run(["git", "remote", "add", "origin", github_repo_url], cwd=project_path, check=True)
        subprocess.run(["git", "branch", "-M", "main"], cwd=project_path, check=True)
        try:
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=project_path, check=True)
            print(f"  ✓ Pushed to {github_repo_url}")
        except Exception:
            print(f"  ⚠ Could not push to GitHub — remote set but push failed")

    # Update global state.json
    import json
    from datetime import datetime
    state = {
        "project": project_name,
        "project_path": str(project_path),
        "phase": "planning",
        "milestone_current": None,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "last_activity": datetime.utcnow().isoformat() + "Z",
        "notes": brief[:120],
    }
    (ROOT / "memory" / "state.json").write_text(json.dumps(state, indent=2))

    print()
    print(f"  ✓ Project created:  projects/{project_name}/")
    print(f"  ✓ Comprehensive BRIEF.md written")
    if github_repo_url:
        print(f"  ✓ GitHub repo:      {github_repo_url}")
    print()
    print("  Start the build:")
    print(f"    python3 frinkloop.py run {project_name}\n")


# ── Feature run ───────────────────────────────────────────────────────────────

def cmd_run(args):
    """Start or resume the agent loop for a project."""
    project_name = _require_project(args)
    _check_env()

    from core.loop import run_loop
    run_loop(project_name, dry_run=args.dry_run, no_hitl=getattr(args, "no_hitl", False))


# ── Feature 4: watch ─────────────────────────────────────────────────────────

def cmd_watch(args):
    """Live dashboard — polls loop state and renders to terminal."""
    project_name = _require_project(args)
    from core.watch import run_watch
    run_watch(project_name)


# ── Feature 2: handoff ────────────────────────────────────────────────────────

def cmd_handoff(args):
    """Snapshot current project state for cross-device continuity."""
    project_name = _require_project(args)
    from core.handoff import create_handoff
    create_handoff(project_name, push=args.push)


# ── Feature 2: wake ───────────────────────────────────────────────────────────

def cmd_wake(args):
    """Resume a project from a handoff snapshot."""
    project_name = _require_project(args)
    _check_env()
    from core.handoff import wake_project
    wake_project(project_name, dry_run=args.dry_run)


# ── status ────────────────────────────────────────────────────────────────────

def cmd_status(args):
    """Print current project status."""
    import json

    project_name = args.project

    if project_name:
        project_path = ROOT / "projects" / project_name
        tasks_path = project_path / "memory" / "tasks.json"
        state_path = project_path / "memory" / "state.json"
    else:
        tasks_path = ROOT / "memory" / "tasks.json"
        state_path = ROOT / "memory" / "state.json"

    _banner("FrinkLoop — Status")

    if state_path.exists():
        state = json.loads(state_path.read_text())
        print(f"  Project:   {state.get('project', '—')}")
        print(f"  Phase:     {state.get('phase', '—')}")
        print(f"  Milestone: {state.get('milestone_current', '—')}")
        print(f"  Notes:     {state.get('notes', '—')[:80]}")
        print()

    if tasks_path.exists():
        try:
            data = json.loads(tasks_path.read_text())
            milestones = data.get("milestones", [])
            for m in milestones:
                tasks = m.get("tasks", [])
                done = sum(1 for t in tasks if t.get("status") == "done")
                total = len(tasks)
                bar = _progress_bar(done, total)
                print(f"  {bar}  {m.get('id','?')} {m.get('name','')[:40]}  ({done}/{total})")
        except Exception as e:
            print(f"  Could not parse tasks: {e}")
    print()


# ── help ─────────────────────────────────────────────────────────────────────

def cmd_help(args=None):
    print(__doc__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _banner(title: str):
    width = max(len(title) + 4, 48)
    print()
    print("  " + "═" * width)
    print(f"  {'  ' + title}")
    print("  " + "═" * width)
    print()


def _prompt(label: str, default: str = "", required: bool = False, secret: bool = False) -> str:
    suffix = " " if not default else f" [{default[:4] + '...' if secret and default else default}] "
    while True:
        try:
            if secret:
                import getpass
                val = getpass.getpass(f"  ? {label}{suffix}")
            else:
                val = input(f"  ? {label}{suffix}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        val = val.strip() or default
        if required and not val:
            print("    This field is required.")
            continue
        return val


def _prompt_multiline(label: str, allow_empty: bool = False) -> str:
    print(f"  ? {label}")
    lines = []
    try:
        while True:
            line = input("    > ")
            if not line and lines:
                break
            if not line and allow_empty:
                break
            if line:
                lines.append(line)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return " ".join(lines)


def _prompt_list(label: str) -> list:
    print(f"  ? {label}:")
    items = []
    try:
        while True:
            item = input("    > ").strip()
            if not item:
                break
            items.append(item)
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return items


def _confirm(label: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    try:
        val = input(f"  ? {label} {hint} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if not val:
        return default
    return val.startswith("y")


def _require_project(args) -> str:
    if not args.project:
        projects = [p.name for p in (ROOT / "projects").iterdir()
                    if p.is_dir() and p.name != "_template"]
        if not projects:
            print("No projects found. Run: python3 frinkloop.py new <name>")
            sys.exit(1)
        if len(projects) == 1:
            return projects[0]
        print("Available projects:")
        for i, p in enumerate(sorted(projects), 1):
            print(f"  [{i}] {p}")
        try:
            choice = input("  ? Select project: ").strip()
            idx = int(choice) - 1
            return sorted(projects)[idx]
        except (ValueError, IndexError, KeyboardInterrupt):
            print("Invalid selection.")
            sys.exit(1)
    return args.project


def _check_env():
    issues = validate_llm_env()
    if issues:
        print(f"{issues[0]}. Run: python3 frinkloop.py init")
        sys.exit(1)


def _progress_bar(done: int, total: int, width: int = 10) -> str:
    if total == 0:
        return "░" * width
    filled = round((done / total) * width)
    return "█" * filled + "░" * (width - filled)


def _create_github_repo(name: str, token: str, description: str) -> str:
    """Create a GitHub repo and return its clone URL."""
    import urllib.request
    import json
    payload = json.dumps({"name": name, "description": description, "private": False, "auto_init": False}).encode()
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=payload,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "User-Agent": "frinkloop",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return data["clone_url"]
    except Exception as e:
        print(f"  ⚠ Could not create GitHub repo: {e}")
        return ""


if __name__ == "__main__":
    main()
