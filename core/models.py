"""
core/models.py — Typed runtime models for FrinkLoop state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Task:
    id: str
    type: str = "code"
    input: str = ""
    agent: str = "developer"
    status: str = "pending"
    milestone: str = ""
    output: str = ""
    acceptance: str = ""
    instruction: str = ""
    depends_on: list[str] = field(default_factory=list)
    fail_count: int = 0
    critic_rejections: int = 0
    result_summary: str = ""
    last_error: str = ""
    created_at: str = ""
    updated_at: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        if "id" not in data:
            raise ValueError("Task is missing required field: id")

        known_keys = {
            "id",
            "type",
            "input",
            "agent",
            "status",
            "milestone",
            "output",
            "acceptance",
            "instruction",
            "depends_on",
            "fail_count",
            "critic_rejections",
            "result_summary",
            "last_error",
            "created_at",
            "updated_at",
        }
        extras = {k: v for k, v in data.items() if k not in known_keys}

        task_type = _as_str(data.get("type"), "").strip() or "code"
        agent = _as_str(data.get("agent"), "").strip()
        if not agent:
            agent_map = {
                "plan": "orchestrator",
                "research": "researcher",
                "code": "developer",
                "test": "qa",
                "review": "critic",
                "docs": "docs",
            }
            agent = agent_map.get(task_type, "developer")

        return cls(
            id=_as_str(data["id"]).strip(),
            type=task_type,
            input=_as_str(data.get("input") or data.get("description"), ""),
            agent=agent,
            status=_as_str(data.get("status"), "pending") or "pending",
            milestone=_as_str(data.get("milestone"), ""),
            output=_as_str(data.get("output"), ""),
            acceptance=_as_str(data.get("acceptance"), ""),
            instruction=_as_str(data.get("instruction"), ""),
            depends_on=[_as_str(item) for item in _as_list(data.get("depends_on")) if _as_str(item)],
            fail_count=_as_int(data.get("fail_count"), 0),
            critic_rejections=_as_int(data.get("critic_rejections"), 0),
            result_summary=_as_str(data.get("result_summary"), ""),
            last_error=_as_str(data.get("last_error"), ""),
            created_at=_as_str(data.get("created_at"), ""),
            updated_at=_as_str(data.get("updated_at"), ""),
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "type": self.type,
            "input": self.input,
            "agent": self.agent,
            "status": self.status,
            "milestone": self.milestone,
            "output": self.output,
            "acceptance": self.acceptance,
            "instruction": self.instruction,
            "depends_on": list(self.depends_on),
            "fail_count": self.fail_count,
            "critic_rejections": self.critic_rejections,
            "result_summary": self.result_summary,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        data.update(self.extras)
        return data


@dataclass
class Milestone:
    id: str
    name: str = ""
    description: str = ""
    status: str = "pending"
    tasks: list[Task] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Milestone":
        if "id" not in data:
            raise ValueError("Milestone is missing required field: id")

        known_keys = {"id", "name", "description", "status", "tasks"}
        extras = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            id=_as_str(data["id"]).strip(),
            name=_as_str(data.get("name"), ""),
            description=_as_str(data.get("description"), ""),
            status=_as_str(data.get("status"), "pending") or "pending",
            tasks=[Task.from_dict(task) for task in _as_list(data.get("tasks"))],
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "tasks": [task.to_dict() for task in self.tasks],
        }
        data.update(self.extras)
        return data


@dataclass
class TaskBoard:
    project: str = ""
    milestone_current: Optional[str] = None
    milestones: list[Milestone] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskBoard":
        raw_milestones = _as_list(data.get("milestones"))
        milestones = [Milestone.from_dict(item) for item in raw_milestones]

        top_level_tasks = _as_list(data.get("tasks"))
        if top_level_tasks and not any(m.tasks for m in milestones):
            milestone_map: dict[str, Milestone] = {m.id: m for m in milestones}
            ordered_ids = [m.id for m in milestones]

            for task_data in top_level_tasks:
                task = Task.from_dict(task_data)
                milestone_id = task.milestone or "1"
                if milestone_id not in milestone_map:
                    milestone_map[milestone_id] = Milestone(id=milestone_id, name=f"Milestone {milestone_id}")
                    ordered_ids.append(milestone_id)
                task.milestone = milestone_id
                milestone_map[milestone_id].tasks.append(task)

            milestones = [milestone_map[milestone_id] for milestone_id in ordered_ids]

        extras = {k: v for k, v in data.items() if k not in {"project", "milestone_current", "milestones", "tasks"}}
        board = cls(
            project=_as_str(data.get("project"), ""),
            milestone_current=_as_str(data.get("milestone_current"), "") or None,
            milestones=milestones,
            extras=extras,
        )
        board.recalculate_progress()
        return board

    def to_dict(self) -> dict[str, Any]:
        data = {
            "project": self.project,
            "milestone_current": self.milestone_current,
            "milestones": [milestone.to_dict() for milestone in self.milestones],
        }
        data.update(self.extras)
        return data

    def all_tasks(self) -> list[Task]:
        return [task for milestone in self.milestones for task in milestone.tasks]

    def completed_task_ids(self) -> set[str]:
        return {task.id for task in self.all_tasks() if task.status == "done"}

    def find_task(self, task_id: str) -> Optional[Task]:
        for task in self.all_tasks():
            if task.id == task_id:
                return task
        return None

    def current_milestone(self) -> Optional[Milestone]:
        if self.milestone_current:
            for milestone in self.milestones:
                if milestone.id == self.milestone_current:
                    return milestone
        for milestone in self.milestones:
            if milestone.status != "done":
                return milestone
        return None

    def recalculate_progress(self) -> None:
        first_incomplete: Optional[str] = None
        for milestone in self.milestones:
            if milestone.tasks and all(task.status == "done" for task in milestone.tasks):
                milestone.status = "done"
            elif milestone.tasks and any(task.status == "in_progress" for task in milestone.tasks):
                milestone.status = "in_progress"
            elif milestone.status == "done" and any(task.status != "done" for task in milestone.tasks):
                milestone.status = "pending"
            elif milestone.status not in {"done", "in_progress", "blocked"}:
                milestone.status = "pending"

            if milestone.status != "done" and first_incomplete is None:
                first_incomplete = milestone.id

        self.milestone_current = first_incomplete
