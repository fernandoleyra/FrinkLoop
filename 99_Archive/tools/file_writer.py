from pathlib import Path
import sys
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

TOOL_DEFINITION = {
    "name": "write_file",
    "description": "Write code, documentation, configs, or any file to the project outputs. Use relative paths — they resolve to outputs/app/ automatically.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path within outputs/app/ or absolute"},
            "content": {"type": "string"},
            "description": {"type": "string", "description": "What this file is (for the artifact log)"}
        },
        "required": ["path", "content"]
    }
}

def run(path: str, content: str, description: str = "") -> str:
    try:
        p = Path(path)
        if not p.is_absolute():
            p = ROOT / "outputs" / "app" / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} chars to {p.relative_to(ROOT)}"
    except Exception as e:
        return f"Write error: {e}"
