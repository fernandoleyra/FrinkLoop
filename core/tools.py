"""
core/tools.py — Tool definitions for agent file and command operations.

Agents call these tools to read/write files and run test commands.
All file operations are sandboxed to the project directory.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


# ── Tool schemas (Anthropic tool_use format) ──────────────────────────────────

TOOL_WRITE_FILE: dict = {
    "name": "write_file",
    "description": (
        "Write or overwrite a file in the project directory. "
        "Use for source files (src/), tests (tests/), and memory notes (memory/)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path from project root, e.g. 'src/api/main.py'",
            },
            "content": {
                "type": "string",
                "description": "Complete file content to write",
            },
        },
        "required": ["path", "content"],
    },
}

TOOL_READ_FILE: dict = {
    "name": "read_file",
    "description": "Read an existing file from the project directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path from project root",
            },
        },
        "required": ["path"],
    },
}

TOOL_RUN_COMMAND: dict = {
    "name": "run_command",
    "description": (
        "Run a safe verification command in the project directory. "
        "Allowed prefixes: pytest, python -m pytest, python3 -m pytest, "
        "python -m py_compile, python3 -m py_compile, tsc --noEmit, "
        "ruff check, mypy, npm test, npx tsc --noEmit."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command to run (must match an allowed prefix)",
            },
        },
        "required": ["command"],
    },
}

TOOL_APPEND_FILE: dict = {
    "name": "append_file",
    "description": (
        "Append text to an existing file. "
        "Use for memory/decisions.md, memory/blockers.md, memory/qa_report.md."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    },
}

# Per-agent tool sets — narrowest set that covers each agent's job
AGENT_TOOLS: dict[str, list[dict]] = {
    "orchestrator": [TOOL_WRITE_FILE, TOOL_READ_FILE, TOOL_APPEND_FILE],
    "developer":    [TOOL_WRITE_FILE, TOOL_READ_FILE, TOOL_RUN_COMMAND, TOOL_APPEND_FILE],
    "qa":           [TOOL_READ_FILE, TOOL_RUN_COMMAND, TOOL_WRITE_FILE, TOOL_APPEND_FILE],
    "critic":       [TOOL_READ_FILE, TOOL_APPEND_FILE],
    "researcher":   [TOOL_WRITE_FILE, TOOL_READ_FILE, TOOL_APPEND_FILE],
}

_ALLOWED_PREFIXES = (
    "pytest",
    "python -m pytest",
    "python -m py_compile",
    "python3 -m pytest",
    "python3 -m py_compile",
    "tsc --noEmit",
    "ruff check",
    "mypy",
    "npm test",
    "npx tsc --noEmit",
)


def get_tools_for_agent(agent: str) -> list[dict]:
    return AGENT_TOOLS.get(agent, [TOOL_READ_FILE])


def execute_tool(name: str, inputs: dict[str, Any], project_path: Path) -> str:
    """Dispatch a tool call and return the result string."""
    try:
        if name == "write_file":
            return _write_file(inputs, project_path)
        if name == "read_file":
            return _read_file(inputs, project_path)
        if name == "run_command":
            return _run_command(inputs, project_path)
        if name == "append_file":
            return _append_file(inputs, project_path)
        return f"Unknown tool: {name}"
    except Exception as exc:
        return f"Tool error ({name}): {exc}"


# ── Tool implementations ───────────────────────────────────────────────────────

def _resolve(raw: str, project_path: Path) -> Path:
    resolved = (project_path / raw).resolve()
    try:
        resolved.relative_to(project_path.resolve())
    except ValueError:
        raise ValueError(f"Path traversal blocked: {raw}")
    return resolved


def _write_file(inputs: dict, project_path: Path) -> str:
    path = _resolve(inputs["path"], project_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(inputs["content"])
    return f"Written {inputs['path']} ({len(inputs['content'])} bytes)"


def _read_file(inputs: dict, project_path: Path) -> str:
    path = _resolve(inputs["path"], project_path)
    if not path.exists():
        return f"File not found: {inputs['path']}"
    content = path.read_text()
    if len(content) > 8000:
        return content[:8000] + f"\n\n[truncated — {len(content)} total bytes]"
    return content


def _run_command(inputs: dict, project_path: Path) -> str:
    cmd = inputs["command"].strip()
    if not any(cmd.startswith(p) for p in _ALLOWED_PREFIXES):
        return f"Not allowed: '{cmd}'. Allowed prefixes: {', '.join(_ALLOWED_PREFIXES)}"
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (result.stdout + result.stderr).strip()
        return f"Exit {result.returncode}:\n{out[:4000]}" if out else f"Exit {result.returncode}: (no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out (60s)"


def _append_file(inputs: dict, project_path: Path) -> str:
    path = _resolve(inputs["path"], project_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text() if path.exists() else ""
    path.write_text(existing + inputs["content"])
    return f"Appended to {inputs['path']}"
