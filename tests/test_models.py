from core.models import TaskBoard


def test_task_board_accepts_nested_milestones():
    board = TaskBoard.from_dict(
        {
            "project": "demo",
            "milestones": [
                {
                    "id": "M1",
                    "name": "First",
                    "tasks": [
                        {"id": "T1", "type": "research", "input": "Look up library", "status": "done"},
                        {"id": "T2", "type": "code", "input": "Build feature"},
                    ],
                }
            ],
        }
    )

    assert board.project == "demo"
    assert board.milestones[0].id == "M1"
    assert board.find_task("T2").type == "code"
    assert board.completed_task_ids() == {"T1"}


def test_task_board_normalizes_legacy_top_level_tasks():
    board = TaskBoard.from_dict(
        {
            "project": "legacy",
            "milestones": [{"id": 1, "name": "Foundation"}],
            "tasks": [
                {"id": "T001", "milestone": 1, "type": "research", "description": "Pick stack"},
                {"id": "T002", "milestone": 1, "type": "code", "input": "Implement scaffold"},
            ],
        }
    )

    assert len(board.milestones) == 1
    assert [task.id for task in board.milestones[0].tasks] == ["T001", "T002"]
    assert board.milestones[0].tasks[0].input == "Pick stack"
    assert board.milestone_current == "1"
