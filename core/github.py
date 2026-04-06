"""
core/github.py — GitHub integration for Agent OS

Provides:
  commit_task(project_path, task)   — git commit after each completed task
  push_to_remote(project_path)      — push to origin if remote is set
  open_issue_for_blocker(...)       — create a GitHub issue from a blocker
  get_repo_info(project_path)       — return (owner, repo_name) from remote URL

Enable by setting GITHUB_TOKEN in your .env file.
All functions are safe to call when GITHUB_TOKEN is absent — they no-op silently.
"""

import os
import re
import subprocess
import urllib.request
import json
import logging
from pathlib import Path

log = logging.getLogger("agent-os")


# ── Public API ────────────────────────────────────────────────────────────────

def commit_task(project_path: Path, task: dict) -> bool:
    """
    Stage all changes in the project and create a conventional commit.
    Commit message: feat(T07): <task input truncated> [agent: developer]

    Returns True if a commit was made, False if nothing changed or no git.
    """
    if not _git_available(project_path):
        return False

    # Stage everything in src/ and tests/ (not memory/ — that's internal)
    staged = _stage_files(project_path)
    if not staged:
        return False

    task_id   = task.get("id", "T?")
    task_type = task.get("type", "code")
    agent     = task.get("agent", "developer")
    summary   = task.get("input", "")[:72].replace("\n", " ")

    # Map task type to conventional commit prefix
    prefix_map = {
        "code":     "feat",
        "test":     "test",
        "review":   "refactor",
        "research": "docs",
        "plan":     "chore",
    }
    prefix = prefix_map.get(task_type, "feat")
    message = f"{prefix}({task_id}): {summary} [agent: {agent}]"

    try:
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=project_path, check=True, capture_output=True,
        )
        log.info(f"Git commit: {message[:80]}")
        return True
    except subprocess.CalledProcessError as e:
        log.debug(f"Git commit failed (may be nothing to commit): {e.stderr.decode()[:100]}")
        return False


def push_to_remote(project_path: Path) -> bool:
    """Push current branch to origin. Returns True on success."""
    if not os.getenv("GITHUB_TOKEN"):
        return False
    if not _has_remote(project_path):
        return False
    try:
        subprocess.run(
            ["git", "push"],
            cwd=project_path, check=True, capture_output=True,
        )
        log.info("Pushed to remote")
        return True
    except subprocess.CalledProcessError as e:
        log.warning(f"Push failed: {e.stderr.decode()[:100]}")
        return False


def open_issue_for_blocker(project_path: Path, task_id: str, reason: str) -> str:
    """
    Create a GitHub issue for a blocker. Returns the issue URL or empty string.
    Requires GITHUB_TOKEN and a remote origin set up.
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return ""

    owner, repo = get_repo_info(project_path)
    if not owner or not repo:
        return ""

    payload = json.dumps({
        "title": f"[Blocker] Task {task_id} failed",
        "body": (
            f"**Task ID**: {task_id}\n\n"
            f"**Reason**:\n{reason}\n\n"
            f"_Opened automatically by Agent OS_"
        ),
        "labels": ["agent-os", "blocker"],
    }).encode()

    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        data=payload,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "User-Agent": "agentos",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            url = data.get("html_url", "")
            log.info(f"GitHub issue opened: {url}")
            return url
    except Exception as e:
        log.warning(f"Could not open GitHub issue: {e}")
        return ""


def get_repo_info(project_path: Path) -> tuple[str, str]:
    """
    Return (owner, repo_name) parsed from the git remote URL.
    Returns ("", "") if no remote or parse fails.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_path, capture_output=True, text=True, timeout=5,
        )
        url = result.stdout.strip()
        # SSH: git@github.com:owner/repo.git
        # HTTPS: https://github.com/owner/repo.git
        m = re.search(r"github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?$", url)
        if m:
            return m.group(1), m.group(2)
    except Exception:
        pass
    return "", ""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _git_available(project_path: Path) -> bool:
    return (project_path / ".git").exists()


def _has_remote(project_path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "remote"],
            cwd=project_path, capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def _stage_files(project_path: Path) -> bool:
    """Stage src/, tests/, and any top-level files. Returns True if anything was staged."""
    try:
        # Add tracked modified files and new files in src/ tests/
        subprocess.run(["git", "add", "src/", "tests/"], cwd=project_path, capture_output=True)
        subprocess.run(["git", "add", "-u"], cwd=project_path, capture_output=True)

        # Check if there's anything staged
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=project_path, capture_output=True, text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False
