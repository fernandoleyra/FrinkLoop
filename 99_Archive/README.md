# NEXUS — AI Development Firm

An elite multi-agent system that builds complex web applications from a briefing to MVP. Modeled on the quantitative rigor of **Renaissance Technologies** and the systems intelligence of **Palantir**.

You talk to one person — the PM. The rest of the firm works autonomously.

---

## Team

| Agent | Role |
|-------|------|
| **PM** | Your interface. Runs intake, plans sprints, drives to MVP |
| **Project Lead** | Permanent devil's advocate. Stress-tests every decision |
| **R&D** | Technical research, stack selection, feasibility analysis |
| **Engineering** | Full-stack code — production quality, not prototypes |
| **UX/Design** | User flows, component specs, design system |
| **Data Analyst** | Metrics framework, schema design, analytics pipelines |
| **Product Visionary** | Market positioning, roadmap, business model |
| **QA/Security** | Test suites, threat modeling, code review |
| **DevOps** | CI/CD, infra-as-code, deployment, monitoring |
| **Biz Strategist** | GTM strategy, pricing, competitive landscape |

---

## Quick Start

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY=your_key_here

# Optional: better web search
export SERPAPI_KEY=your_serpapi_key

# 2. Make runnable and launch
chmod +x run.sh
./run.sh

# Or pass a briefing directly:
./run.sh "I want to build a SaaS tool for freelancers to track invoices and clients"
```

---

## How it works

### 1. Intake (you + PM)
The PM asks 4–6 structural questions to clarify **What**, **How**, and **Output**. You answer, the PM synthesizes a project spec.

### 2. Project Lead review
The Project Lead stress-tests the spec — identifying risks, gaps, and bad assumptions — before any code is written.

### 3. Sprint loop (autonomous)
The PM plans sprints, dispatches agents, and iterates continuously. Agents share memory, build on each other's outputs, and write real files to `outputs/`.

The loop only pauses when:
- MVP is reached
- You type `stop`
- A genuine blocker requires your input

### 4. Output
Everything lands in `outputs/`:
```
outputs/
├── SPEC.md              # Living project spec
├── HANDOFF.md           # Final report when done
├── app/                 # All generated code
│   ├── app/             # Next.js app or equivalent
│   ├── api/             # Backend routes
│   ├── components/      # UI components
│   ├── db/              # Schema and migrations
│   └── tests/           # Test suites
└── docs/                # Docs from each agent each sprint
    ├── rd_sprint_1.md
    ├── engineering_sprint_1.md
    ├── design_sprint_1.md
    └── ...
```

---

## Configuration

Edit `agent.yaml` to change:
- `model.name` — swap to `claude-opus-4-5` for maximum intelligence
- `iteration.max_sprints` — how many sprints before hard stop
- `memory.type` — `sqlite` (default) or `chromadb` for vector memory

---

## Running tests

```bash
source .venv/bin/activate
pip install pytest
python -m pytest tests/ -v
```

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `SERPAPI_KEY` | No | SerpAPI key for enhanced web search |
| `NEXUS_LOG_LEVEL` | No | `DEBUG` or `INFO` (default `INFO`) |
