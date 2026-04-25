# FrinkLoop V2 Plan

## Goal

Turn FrinkLoop from a prompt-driven sequential loop into a reliable autonomous software-delivery runtime with typed state, blocking gates, resumable execution, and measurable behavior.

## Current Diagnosis

The current system already has the right product shell:

- brief-driven project creation
- a project-local memory model
- CLI entrypoints for run, watch, handoff, and wake
- agent role separation
- escalation and human override paths

The runtime underneath is still too loose for long autonomous runs:

- task completion is inferred from a raw model response instead of a parsed result contract
- QA and Critic are described as gates but are not enforced as runtime gates
- task schema in docs and task schema in code do not match
- state persistence is plain file I/O with no locking or durable event model
- milestone advancement and task lifecycle are only partially modeled
- context loading is based on truncation, not relevance
- observability is limited to logs and terminal snapshots
- repository validation is not isolated from generated project tests

## Design Principles

- Keep the FrinkLoop product surface opinionated and simple
- Strengthen the runtime before adding more agent roles
- Make state machine behavior explicit, typed, and testable
- Treat test, review, and security as first-class gates
- Preserve file-based project memory for human inspection, but back it with stronger persistence
- Optimize for software delivery, not general-purpose multi-agent orchestration

## Target Architecture

### 1. Typed Run State

Introduce typed runtime models for:

- `RunState`
- `Milestone`
- `Task`
- `TaskAttempt`
- `AgentResult`
- `GateResult`
- `Blocker`

Recommended implementation:

- add `core/models.py` with Pydantic models
- replace ad hoc dictionary access in `core/loop.py`, `core/memory.py`, and `core/escalation.py`
- make `core/task-schema.md` generated from the runtime models or remove it as a separate source of truth

### 2. Explicit Task Lifecycle

Replace the current loose statuses with a proper lifecycle:

- `pending`
- `ready`
- `in_progress`
- `awaiting_qa`
- `awaiting_review`
- `awaiting_security`
- `done`
- `blocked`
- `failed`
- `escalated`
- `skipped`

Each transition should be made by runtime logic, not by convention in prompts.

### 3. Parsed Agent Result Contract

Require every spawned agent to return a structured payload:

- `status`
- `summary`
- `files_written`
- `files_read`
- `tests_run`
- `followups`
- `blocker_reason`

Recommended implementation:

- add `core/contracts.py`
- make `core/spawn.py` parse structured JSON from model output
- reject or retry malformed outputs

### 4. Blocking Quality Gates

A code task must not be marked `done` directly after code generation.

Required gate chain:

1. developer produces artifacts
2. QA validates the artifacts and writes a structured report
3. Critic performs review and returns pass or reject
4. optional security gate runs for relevant changes
5. runtime marks task complete only if required gates pass

Recommended implementation:

- split task execution and gate execution in `core/loop.py`
- add `core/gates.py`
- track `critic_rejections`, `qa_failures`, and `security_failures` independently

### 5. Durable State

Keep `memory/` as the human-readable projection, but stop treating it as the primary transactional store.

Recommended implementation:

- add a SQLite run store in `core/store.py`
- persist runs, tasks, attempts, blockers, and gate results
- regenerate `memory/*.json` and `memory/*.md` as projections after state changes
- use file locks or transactional writes for projection files

### 6. Retrieval-Based Context Assembly

Move from fixed slicing to relevance-aware context packing.

Recommended implementation:

- add task-scoped context builders in `core/context.py`
- prioritize:
  - current task input
  - dependencies and outputs
  - recent decisions
  - related blockers
  - touched files
  - relevant research notes
- stop dumping whole files with arbitrary character caps

### 7. Parallel Safe Execution

FrinkLoop currently behaves like a single-worker scheduler.

Recommended V2 parallelism:

- allow multiple `research` tasks with no dependency overlap
- allow review and security to run in parallel after QA pass
- keep code tasks serialized at first unless file ownership is explicit

Recommended implementation:

- add a scheduler layer that emits runnable tasks
- add task ownership metadata
- add per-task file scope or module scope to avoid collisions

### 8. Observability and Evaluation

The runtime needs measurable signals.

Track at minimum:

- task latency by type
- retries by type
- blocker counts by category
- pass rate for QA and Critic
- escalation frequency
- token use and cost per task
- time to milestone completion

Recommended implementation:

- add `core/metrics.py`
- emit a machine-readable run log such as `memory/run_metrics.json`
- extend `watch` to display gate failures, retries, and active blockers

### 9. Platform Test Isolation

The repo currently mixes platform tests with generated project tests.

Recommended implementation:

- add root `tests/` covering `core/` and `frinkloop.py`
- add `pytest.ini` to scope platform tests by default
- move example project tests outside default collection or mark them separately
- add smoke tests for:
  - new project creation
  - plan generation dry run
  - status transitions
  - blocker escalation
  - handoff and wake

## Phased Delivery

## Phase 1: Runtime Integrity

Target:

- typed models
- unified schema
- structured agent result parsing
- isolated root test suite

Files:

- `core/models.py`
- `core/contracts.py`
- `core/memory.py`
- `core/spawn.py`
- `core/loop.py`
- `tests/`

Exit criteria:

- no direct `dict` state mutation in the loop core
- malformed agent responses fail deterministically
- root tests run without collecting project fixtures

## Phase 2: Real Gates

Target:

- QA and Critic become runtime-enforced
- code tasks can no longer bypass validation

Files:

- `core/loop.py`
- `core/gates.py`
- `core/escalation.py`
- `agents/qa.md`
- `agents/critic.md`

Exit criteria:

- `code` task transitions through QA and review before `done`
- gate failures produce explicit blocker or retry records

## Phase 3: Durable Store and Projections

Target:

- SQLite-backed state
- projection files in `memory/`

Files:

- `core/store.py`
- `core/memory.py`
- `core/handoff.py`
- `core/watch.py`

Exit criteria:

- run state survives interrupted execution without file corruption
- projection files can be regenerated from store state

## Phase 4: Smarter Context and Scheduling

Target:

- relevance-based context assembly
- safe parallel research execution

Files:

- `core/context.py`
- `core/scheduler.py`
- `core/spawn.py`
- `core/loop.py`

Exit criteria:

- context size remains bounded on larger projects
- independent research tasks can run concurrently

## Phase 5: Metrics and Dashboard

Target:

- measurable runtime behavior
- richer watch mode

Files:

- `core/metrics.py`
- `core/watch.py`
- `core/obsidian.py`

Exit criteria:

- watch shows task state plus gate state
- run metrics are recorded for every task attempt

## Immediate Execution Order

This is the recommended implementation order for the next coding passes:

1. fix `.gitignore` so repo tooling is reliable
2. add root `tests/` and `pytest.ini`
3. introduce `core/models.py` and unify task schema
4. introduce structured agent result parsing in `core/spawn.py`
5. refactor `core/loop.py` to stop marking tasks `done` immediately after any agent output
6. add explicit QA and Critic gates
7. add durable state store

## Non-Goals For V2

- adding more agent personas before the runtime is stable
- optimizing for generalized business workflows
- adding heavy UI before the scheduler and gates are reliable
- implementing unrestricted parallel code editing in the first pass

## Success Criteria

FrinkLoop V2 should be considered successful when:

- the loop is resumable without manual JSON repair
- task status transitions are deterministic and test-covered
- no code task reaches `done` without passing required gates
- runtime state has a single source of truth
- context assembly scales beyond small repos
- platform tests can be run independently from generated project outputs
