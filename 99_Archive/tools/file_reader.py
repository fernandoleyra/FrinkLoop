from pathlib import Path

TOOL_DEFINITION = {
    "name": "read_file",
    "description": "Read any file in the project (code, docs, configs, existing outputs).",
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"]
    }
}

def run(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return f"File not found: {path}"
        if p.stat().st_size > 500_000:
            return f"File too large ({p.stat().st_size} bytes)"
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Read error: {e}"
