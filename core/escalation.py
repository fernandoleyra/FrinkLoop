"""
core/escalation.py — Escalation rules

Checks whether any condition requires pausing the loop and notifying the human.
All conditions are checked before each iteration.
"""

from pathlib import Path
from typing import Optional


# Max consecutive failures before escalating
MAX_TASK_FAILURES = 5

# Max Critic rejections of same task before escalating
MAX_CRITIC_REJECTIONS = 3


def check_escalation(tasks: dict, memory) -> Optional[str]:
    """
    Check all escalation conditions.

    Returns:
        A human-readable escalation message if any condition is triggered.
        None if the loop should continue normally.
    """

    # Rule 1: Same task failed too many times
    for milestone in tasks.get("milestones", []):
        for task in milestone.get("tasks", []):
            fail_count = task.get("fail_count", 0)
            if fail_count >= MAX_TASK_FAILURES:
                return (
                    f"Task {task['id']} has failed {fail_count} times.\n"
                    f"Task: {task.get('input', '')[:200]}\n"
                    f"Last error: {task.get('last_error', 'unknown')}\n\n"
                    "Please review memory/blockers.md and advise how to proceed."
                )

    # Rule 2: Critic rejected same task too many times
    for milestone in tasks.get("milestones", []):
        for task in milestone.get("tasks", []):
            rejection_count = task.get("critic_rejections", 0)
            if rejection_count >= MAX_CRITIC_REJECTIONS:
                return (
                    f"Task {task['id']} has been rejected by Critic {rejection_count} times.\n"
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
