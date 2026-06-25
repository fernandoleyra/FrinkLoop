"""
NEXUS — product_visionary Agent
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tools import TOOLS, dispatch_tool
from agents.shared import get_client, load_prompt, load_config, run_agent_loop, save_artifact

CLIENT = get_client()
SYSTEM = load_prompt("product_visionary")
CONFIG = load_config()


def run(task: str, spec: str = "", sprint: int = 0) -> str:
    return run_agent_loop(
        client=CLIENT,
        system=SYSTEM,
        task=task,
        spec=spec,
        sprint=sprint,
        tools=TOOLS,
        dispatch_fn=dispatch_tool,
        agent_name="product_visionary",
    )
