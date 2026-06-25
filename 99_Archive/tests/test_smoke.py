"""
tests/test_smoke.py — Basic sanity checks for NEXUS.
Run with: python -m pytest tests/ -v
"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def test_config_loads():
    import yaml
    config = yaml.safe_load((ROOT / "agent.yaml").read_text())
    assert config["name"] == "nexus"
    assert "agents" in config
    assert len(config["agents"]) >= 9


def test_all_prompts_exist():
    config_agents = [
        "pm", "project_lead", "rd", "engineering", "ux_design",
        "data_analyst", "product_visionary", "qa_security", "devops", "biz_strategist"
    ]
    for name in config_agents:
        path = ROOT / "prompts" / f"{name}.txt"
        assert path.exists(), f"Missing prompt: prompts/{name}.txt"
        assert len(path.read_text()) > 100, f"Prompt too short: {name}.txt"


def test_all_agent_files_exist():
    agent_files = [
        "pm", "project_lead", "rd", "engineering", "ux_design",
        "data_analyst", "product_visionary", "qa_security", "devops", "biz_strategist",
        "shared"
    ]
    for name in agent_files:
        path = ROOT / "agents" / f"{name}.py"
        assert path.exists(), f"Missing agent: agents/{name}.py"


def test_tools_load():
    import importlib.util
    tools_dir = ROOT / "tools"
    loaded = 0
    for f in tools_dir.glob("*.py"):
        if f.stem.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "TOOL_DEFINITION") and hasattr(mod, "run"):
            loaded += 1
    assert loaded >= 7, f"Expected at least 7 tools, found {loaded}"


def test_db_init():
    from agents.shared import init_db, kv_set, kv_get
    init_db()
    kv_set("test_key", "test_value")
    val = kv_get("test_key")
    assert val == "test_value"


def test_shared_utilities():
    from agents.shared import (
        load_config, load_prompt,
        save_spec, load_spec,
        log_sprint, load_sprint_log,
    )
    config = load_config()
    assert config is not None

    prompt = load_prompt("pm")
    assert "PM" in prompt or "Project Manager" in prompt

    save_spec("## Test Spec\nTest project.")
    spec = load_spec()
    assert "Test Spec" in spec


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
