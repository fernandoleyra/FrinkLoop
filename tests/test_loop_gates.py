from pathlib import Path

from core.contracts import AgentResult
from core.loop import run_quality_gates
from core.memory import Memory
from core.models import Task


def test_run_quality_gates_pass(monkeypatch, tmp_path: Path):
    calls = []

    def fake_spawn(agent, task, project_path, dry_run=False):
        calls.append(agent)
        if agent == "qa":
            return AgentResult(
                status="complete",
                summary="qa passed",
                raw_output="",
                tests_run=["pytest tests/test_feature.py"],
            )
        return AgentResult(
            status="complete",
            summary="critic approved",
            raw_output="",
            followups=["cleanup later"],
        )

    monkeypatch.setattr("core.loop.spawn_agent", fake_spawn)

    gate_name, gate_result, metadata = run_quality_gates(
        Task(id="T1", type="code", input="Build feature", milestone="M1"),
        tmp_path,
        dry_run=False,
    )

    assert calls == ["qa", "critic"]
    assert gate_name is None
    assert gate_result is None
    assert metadata["qa_summary"] == "qa passed"
    assert metadata["critic_summary"] == "critic approved"


def test_run_quality_gates_stops_on_qa_failure(monkeypatch, tmp_path: Path):
    calls = []

    def fake_spawn(agent, task, project_path, dry_run=False):
        calls.append(agent)
        return AgentResult(status="failed", summary="tests failed", raw_output="")

    monkeypatch.setattr("core.loop.spawn_agent", fake_spawn)

    gate_name, gate_result, metadata = run_quality_gates(
        Task(id="T1", type="code", input="Build feature", milestone="M1"),
        tmp_path,
        dry_run=False,
    )

    assert calls == ["qa"]
    assert gate_name == "qa"
    assert gate_result.summary == "tests failed"
    assert metadata["qa_summary"] == "tests failed"


def test_increment_critic_rejections(tmp_path: Path):
    memory = Memory(tmp_path / "project")
    memory.save_tasks(
        {
            "project": "demo",
            "milestones": [
                {
                    "id": "M1",
                    "tasks": [
                        {"id": "T1", "type": "code", "input": "Build feature", "milestone": "M1"}
                    ],
                }
            ],
        }
    )

    count = memory.increment_critic_rejections("T1")
    assert count == 1
    board = memory.load_tasks()
    assert board.find_task("T1").critic_rejections == 1
