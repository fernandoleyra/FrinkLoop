import json
from pathlib import Path

from core.contracts import AgentResult
from core.loop import _materialize_planning_artifacts


def test_materialize_planning_artifacts_writes_plan_and_tasks(tmp_path: Path):
    project_path = tmp_path / "my-app"
    (project_path / "memory").mkdir(parents=True)

    result = AgentResult(
        status="complete",
        summary="Project plan created",
        raw_output="",
        payload={
            "summary": "Project plan created",
            "plan_markdown": "# Plan\n\n## Goal\nBuild app\n",
            "tasks_board": {
                "project": "my-app",
                "milestones": [
                    {
                        "id": "M1",
                        "name": "Foundation",
                        "tasks": [
                            {
                                "id": "T1",
                                "milestone": "M1",
                                "type": "research",
                                "input": "Choose stack",
                            }
                        ],
                    }
                ],
            },
            "decisions_entry": "## 2026-04-11 22:10\n**Decision:** Use FastAPI\n**Reason:** Simple API stack\n",
        },
    )

    _materialize_planning_artifacts(project_path, result)

    assert (project_path / "memory" / "plan.md").exists()
    assert (project_path / "memory" / "tasks.json").exists()
    assert (project_path / "memory" / "decisions.md").exists()

    data = json.loads((project_path / "memory" / "tasks.json").read_text())
    assert data["project"] == "my-app"
    assert data["milestones"][0]["tasks"][0]["id"] == "T1"


def test_materialize_planning_artifacts_from_raw_output_sections(tmp_path: Path):
    project_path = tmp_path / "my-app"
    (project_path / "memory").mkdir(parents=True)

    raw_output = """**memory/plan.md**

# Plan

## Goal
Build app

**memory/tasks.json**

```
{
  "project": "my-app",
  "milestones": [
    {
      "id": "M1",
      "name": "Foundation",
      "tasks": [
        {
          "id": "T1",
          "milestone": "M1",
          "type": "research",
          "input": "Choose stack"
        }
      ]
    }
  ]
}
```
**memory/decisions.md**

## Decision
Use FastAPI
"""

    result = AgentResult(
        status="complete",
        summary="Project plan created",
        raw_output=raw_output,
        payload={
            "summary": "Project plan created",
            "plan_markdown": "memory/plan.md",
            "tasks_board": "memory/tasks.json",
            "decisions_entry": "memory/decisions.md",
        },
    )

    _materialize_planning_artifacts(project_path, result)

    assert (project_path / "memory" / "plan.md").exists()
    assert (project_path / "memory" / "tasks.json").exists()
    assert (project_path / "memory" / "decisions.md").exists()

    data = json.loads((project_path / "memory" / "tasks.json").read_text())
    assert data["project"] == "my-app"
    assert data["milestones"][0]["tasks"][0]["id"] == "T1"


def test_materialize_planning_artifacts_normalizes_initial_task_statuses(tmp_path: Path):
    project_path = tmp_path / "my-app"
    (project_path / "memory").mkdir(parents=True)

    result = AgentResult(
        status="complete",
        summary="Project plan created",
        raw_output="",
        payload={
            "summary": "Project plan created",
            "plan_markdown": "# Plan\n\n## Goal\nBuild app\n",
            "tasks_board": {
                "project": "my-app",
                "milestones": [
                    {
                        "id": "M1",
                        "name": "Core App Functionality",
                        "status": "in_progress",
                        "tasks": [
                            {
                                "id": "T1",
                                "type": "code",
                                "agent": "developer",
                                "status": "done",
                                "milestone": "M1",
                                "input": "Implement user registration using Supabase",
                                "output": "src/register/index.swift",
                                "acceptance": "Users can register successfully",
                            },
                            {
                                "id": "T2",
                                "type": "code",
                                "agent": "developer",
                                "status": "in_progress",
                                "milestone": "M1",
                                "input": "Display dashboard with user profiles",
                                "output": "src/dashboard/index.swift",
                                "acceptance": "Dashboard displays user profiles correctly",
                            }
                        ]
                    }
                ],
            },
            "decisions_entry": "## Decision\nUse FastAPI\n",
        },
    )

    _materialize_planning_artifacts(project_path, result)

    tasks = json.loads((project_path / "memory" / "tasks.json").read_text())
    assert tasks["milestones"][0]["tasks"][0]["status"] == "done"
    assert tasks["milestones"][0]["tasks"][1]["status"] == "pending"
