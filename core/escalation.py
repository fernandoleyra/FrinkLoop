"""
core/escalation.py — Escalation rules

Checks whether any condition requires pausing the loop and notifying the human.
All conditions are checked before each iteration.
"""

from pathlib import Path
from typing import Optional

from core.models import TaskBoard
import core.config as cfg

MAX_TASK_FAILURES    = cfg.get("loop", "max_task_retries",       5)
MAX_CRITIC_REJECTIONS = cfg.get("loop", "max_critic_rejections", 3)


def check_escalation(tasks: TaskBoard, memory) -> Optional[str]:
    """
    Check all escalation conditions.

    Returns:
        A human-readable escalation message if any condition is triggered.
        None if the loop should continue normally.
    """

    # Rule 1: Same task failed too many times
    for milestone in tasks.milestones:
        for task in milestone.tasks:
            fail_count = task.fail_count
            if fail_count >= MAX_TASK_FAILURES:
                return (
                    f"Task {task.id} has failed {fail_count} times.\n"
                    f"Task: {task.input[:200]}\n"
                    f"Last error: {task.last_error or 'unknown'}\n\n"
                    "Please review memory/blockers.md and advise how to proceed."
                )

    # Rule 2: Critic rejected same task too many times
    for milestone in tasks.milestones:
        for task in milestone.tasks:
            rejection_count = task.critic_rejections
            if rejection_count >= MAX_CRITIC_REJECTIONS:
                return (
                    f"Task {task.id} has been rejected by Critic {rejection_count} times.\n"
                    "The Developer and Critic cannot agree on the implementation.\n"
                    "Please review memory/critic_review.md and make a decision."
                )

    # Rule 3: Security vulnerability in blocker
    blockers = memory.read_blockers()
    if "SECURITY" in blockers.upper() or "VULNERABILITY" in blockers.upper():
        return (
            "A potential security issue was flagged in memory/blockers.md.\n"
            "Please review before the build continues."
        )

    return None
