# Task Schema — How Tasks Are Structured

## tasks.json Structure

{
  "project": "project-name",
  "milestone_current": "M1",
  "milestones": [
    {
      "id": "M1",
      "name": "Milestone name",
      "description": "What done looks like",
      "status": "pending | in_progress | done | blocked",
      "tasks": [
        {
          "id": "T001",
          "milestone": "M1",
          "type": "research | code | test | review | docs | plan",
          "agent": "orchestrator | researcher | developer | qa | critic | docs",
          "input": "Detailed description of what to build",
          "acceptance": "What success looks like",
          "depends_on": ["T000"],
          "status": "pending | in_progress | done | blocked | failed | skipped",
          "fail_count": 0,
          "critic_rejections": 0,
          "output": "",
          "result_summary": "",
          "last_error": "",
          "created_at": "ISO timestamp",
          "updated_at": "ISO timestamp"
        }
      ]
    }
  ]
}

## Status Flow

pending → in_progress → done
        ↘
         blocked | failed | skipped

## Task ID Convention
T001, T002, T003... per project
Fix tasks get suffix: T001-fix1, T001-fix2

## Dependency Rules
- A task cannot start until all depends_on tasks are "done"
- Tasks with no depends_on can run in parallel
- Legacy top-level `tasks[]` input is normalized into the nested milestone format
