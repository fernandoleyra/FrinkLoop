# Task Schema — How Tasks Are Structured

## tasks.json Structure

{
  "project": "project-name",
  "milestone_current": 1,
  "milestones": [
    {
      "id": 1,
      "name": "Milestone name",
      "description": "What done looks like",
      "status": "pending | in-progress | complete"
    }
  ],
  "tasks": [
    {
      "id": "T001",
      "milestone": 1,
      "title": "Short imperative title",
      "description": "Detailed description of what to build",
      "agent": "dev | qa | critic | docs | researcher",
      "depends_on": ["T000"],
      "status": "pending | in-progress | done | blocked | qa-failed | changes-required | approved",
      "attempts": 0,
      "output": "",
      "created_at": "ISO timestamp",
      "updated_at": "ISO timestamp"
    }
  ]
}

## Status Flow

pending → in-progress → done → qa-failed OR approved
                              ↓
                         changes-required → in-progress (fix loop)

blocked → (Orchestrator reassigns or escalates)

## Task ID Convention
T001, T002, T003... per project
Fix tasks get suffix: T001-fix1, T001-fix2

## Dependency Rules
- A task cannot start until all depends_on tasks are "approved"
- Tasks with no depends_on can run in parallel
- Orchestrator decides parallelism based on available context
