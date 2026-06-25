"""
tools/__init__.py — Auto-discovers and registers all NEXUS tools.
Each tool module must define:
  - TOOL_DEFINITION: dict (Anthropic tool schema)
  - run(**kwargs) -> str
"""
import importlib
from pathlib import Path

TOOL_MODULES = {}
TOOLS = []

_tools_dir = Path(__file__).parent

for _file in sorted(_tools_dir.glob("*.py")):
    if _file.stem.startswith("_"):
        continue
    try:
        _module = importlib.import_module(f"tools.{_file.stem}")
        if hasattr(_module, "TOOL_DEFINITION") and hasattr(_module, "run"):
            TOOL_MODULES[_module.TOOL_DEFINITION["name"]] = _module
            TOOLS.append(_module.TOOL_DEFINITION)
    except Exception as e:
        print(f"  [tools] Warning: could not load {_file.stem}: {e}")


def dispatch_tool(name: str, inputs: dict) -> str:
    if name not in TOOL_MODULES:
        return f"Error: unknown tool '{name}'. Available: {list(TOOL_MODULES.keys())}"
    try:
        return str(TOOL_MODULES[name].run(**inputs))
    except Exception as e:
        return f"Error running '{name}': {e}"
