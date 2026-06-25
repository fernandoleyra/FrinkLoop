"""
NEXUS — Project Lead Agent (Devil's Advocate)
Stress-tests specs, sprint plans, and outputs. The PL's job is to find
what's wrong before it ships — not to block progress, but to make it unbreakable.
"""

import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from tools import TOOLS, dispatch_tool
from agents.shared import get_client, load_prompt, load_config, run_agent_loop

CLIENT = get_client()
SYSTEM = load_prompt("project_lead")
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
        agent_name="project_lead",
    )
