import subprocess

ALLOWED = {"ls", "find", "cat", "head", "tail", "grep", "wc", "echo", "pwd", "date", "tree", "which", "python3"}

TOOL_DEFINITION = {
    "name": "shell_command",
    "description": "Run safe shell commands to inspect the project directory, check files, or validate outputs.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
    }
}

def run(command: str) -> str:
    base = command.strip().split()[0]
    if base not in ALLOWED:
        return f"Command '{base}' not allowed. Allowed: {sorted(ALLOWED)}"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        return (result.stdout + result.stderr)[:4000]
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return f"Error: {e}"
