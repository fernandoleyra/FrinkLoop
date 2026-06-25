import subprocess, tempfile, os
from pathlib import Path
ROOT = Path(__file__).parent.parent

TOOL_DEFINITION = {
    "name": "execute_python",
    "description": "Execute Python code for data analysis, prototyping, validation, schema generation, or any computation. Returns stdout/stderr.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer", "default": 60}
        },
        "required": ["code"]
    }
}

def run(code: str, timeout: int = 60) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        result = subprocess.run(
            ["python3", tmp],
            capture_output=True, text=True, timeout=timeout, cwd=str(ROOT)
        )
        out = result.stdout
        if result.stderr:
            out += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            out += f"\n(exit {result.returncode})"
        return out[:8000] or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        return f"Execution error: {e}"
    finally:
        os.unlink(tmp)
