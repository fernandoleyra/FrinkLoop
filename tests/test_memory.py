import json
from pathlib import Path

from core.memory import Memory


def test_update_task_status_persists_metadata(tmp_path: Path):
    project_path = tmp_path / "project"
    memory = Memory(project_path)
    memory.save_tasks(
        {
            "project": "demo",
            "milestones": [
                {
                    "id": "M1",
                    "name": "First",
                    "tasks": [
                        {"id": "T1", "type": "code", "input": "Build feature", "status": "pending", "milestone": "M1"}
                    ],
                }
            ],
        }
    )

    memory.update_task_status(
        "T1",
        "done",
        result="built feature",
        metadata={
            "files_written": ["src/feature.py"],
            "tests_run": ["pytest tests/test_feature.py"],
            "followups": ["add integration test"],
        },
    )

    data = json.loads((project_path / "memory" / "tasks.json").read_text())
    task = data["milestones"][0]["tasks"][0]
    assert task["result_summary"] == "built feature"
    assert task["files_written"] == ["src/feature.py"]
    assert task["tests_run"] == ["pytest tests/test_feature.py"]
    assert task["followups"] == ["add integration test"]
