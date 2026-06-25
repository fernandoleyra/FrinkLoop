"""
agents/shared.py — utilities shared across all NEXUS agents.
"""

import anthropic
import sqlite3
import json
import yaml
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "memory" / "nexus.db"


# ── Client & config ────────────────────────────────────────────────────────────

def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def load_config() -> dict:
    return yaml.safe_load((ROOT / "agent.yaml").read_text())


def load_prompt(agent_name: str) -> str:
    path = ROOT / "prompts" / f"{agent_name}.txt"
    if path.exists():
        return path.read_text()
    return f"You are the {agent_name} agent in the NEXUS development firm."


# ── DB init ────────────────────────────────────────────────────────────────────

def init_db():
    Path(DB_PATH).parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS project_spec (
            id INTEGER PRIMARY KEY,
            content TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sprint_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sprint_number INTEGER NOT NULL,
            goal TEXT,
            results TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            sprint INTEGER NOT NULL,
            task TEXT,
            output TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            agent TEXT,
            sprint INTEGER,
            description TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS open_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            raised_by TEXT,
            sprint INTEGER,
            resolved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        );
    """)
    conn.commit()
    conn.close()


init_db()


# ── Spec ──────────────────────────────────────────────────────────────────────

def save_spec(content: str):
    conn = sqlite3.connect(DB_PATH)
    ts = datetime.utcnow().isoformat()
    conn.execute("DELETE FROM project_spec")
    conn.execute("INSERT INTO project_spec (content, updated_at) VALUES (?, ?)", (content, ts))
    conn.commit()
    conn.close()
    # Also write to file for easy reading
    (ROOT / "outputs" / "SPEC.md").parent.mkdir(exist_ok=True)
    (ROOT / "outputs" / "SPEC.md").write_text(content)


def load_spec() -> str:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT content FROM project_spec ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row[0] if row else ""


# ── Sprint log ────────────────────────────────────────────────────────────────

def log_sprint(sprint_number: int, goal: str, results: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO sprint_log (sprint_number, goal, results, created_at) VALUES (?,?,?,?)",
        (sprint_number, goal, json.dumps(results), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def load_sprint_log() -> list:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT sprint_number, goal, results, created_at FROM sprint_log ORDER BY id"
    ).fetchall()
    conn.close()
    return [
        {"sprint": r[0], "goal": r[1], "results": json.loads(r[2] or "{}"), "at": r[3]}
        for r in rows
    ]


# ── Decisions ─────────────────────────────────────────────────────────────────

def log_decision(agent: str, sprint: int, task: str, output: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO agent_decisions (agent, sprint, task, output, created_at) VALUES (?,?,?,?,?)",
        (agent, sprint, task, output, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


# ── Artifacts ─────────────────────────────────────────────────────────────────

def save_artifact(name: str, path: str, agent: str, sprint: int, description: str = ""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO artifacts (name, path, agent, sprint, description, created_at) VALUES (?,?,?,?,?,?)",
        (name, path, agent, sprint, description, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def load_artifacts() -> list:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT name, path, agent, sprint, description FROM artifacts ORDER BY id"
    ).fetchall()
    conn.close()
    return [{"name": r[0], "path": r[1], "agent": r[2], "sprint": r[3], "desc": r[4]} for r in rows]


# ── KV memory ─────────────────────────────────────────────────────────────────

def kv_set(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO kv (key, value, updated_at) VALUES (?,?,?)",
        (key, value, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def kv_get(key: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else None


# ── Generic agent loop ────────────────────────────────────────────────────────

def run_agent_loop(
    client: anthropic.Anthropic,
    system: str,
    task: str,
    spec: str,
    sprint: int,
    tools: list,
    dispatch_fn,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8192,
    agent_name: str = "agent",
) -> str:
    """
    Standard agentic loop reused by every NEXUS agent.
    Injects the current spec and sprint number into every task.
    """
    full_task = f"""Sprint: {sprint}

Project Spec:
{spec}

Your Task:
{task}
"""
    messages = [{"role": "user", "content": full_task}]

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = dispatch_fn(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Task completed."
