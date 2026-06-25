import sqlite3
from pathlib import Path
ROOT = Path(__file__).parent.parent
DB = ROOT / "memory" / "nexus.db"

TOOL_DEFINITION = {
    "name": "memory_recall",
    "description": "Recall a stored insight, decision, or fact from shared team memory by key. Use to check what other agents have already decided.",
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key to look up, or 'ALL' for full memory dump"}
        },
        "required": ["key"]
    }
}

def run(key: str) -> str:
    try:
        conn = sqlite3.connect(DB)
        if key.upper() == "ALL":
            rows = conn.execute("SELECT key, value, updated_at FROM kv ORDER BY updated_at DESC LIMIT 50").fetchall()
            conn.close()
            if not rows:
                return "Memory is empty."
            return "\n".join(f"[{r[2][:10]}] {r[0]}: {r[1]}" for r in rows)
        row = conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else f"No memory for key: {key}"
    except Exception as e:
        return f"Recall error: {e}"
