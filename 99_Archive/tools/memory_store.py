import sqlite3
from pathlib import Path
from datetime import datetime
ROOT = Path(__file__).parent.parent
DB = ROOT / "memory" / "nexus.db"

TOOL_DEFINITION = {
    "name": "memory_store",
    "description": "Store a key insight, decision, constraint, or fact in shared team memory. Other agents can recall it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Short identifier (e.g. 'auth_strategy', 'db_choice')"},
            "value": {"type": "string"}
        },
        "required": ["key", "value"]
    }
}

def run(key: str, value: str) -> str:
    try:
        conn = sqlite3.connect(DB)
        conn.execute(
            "INSERT OR REPLACE INTO kv (key, value, updated_at) VALUES (?,?,?)",
            (key, value, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        return f"Stored: {key}"
    except Exception as e:
        return f"Memory error: {e}"
