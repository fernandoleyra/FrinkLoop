# FrinkLoop Plan 9 — Caveman Integration + Plugin Polish + Acknowledgements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Wire the caveman token-compression directive into the actual subagent dispatch paths in `mvp-loop`, confirm the stop hook exit-code convention is documented accurately, bump `plugin.json` to v0.9.0, add acknowledgements to the plugin README, and tighten up any loose ends discovered during Plans 1-8.

**Architecture:** "Caveman" is a prompt-prefix directive that strips subagent prompts to a compact, telegraphic style. FrinkLoop already references compression in config.yaml and mentions it in SKILL.md — Plan 9 adds a concrete `caveman_prefix` helper and documents the dispatch pattern. Plugin polish: version bump, stop hook exit-code clarification, README acknowledgements.

**Tech Stack:** Bash only. No new dependencies.

---

## File Structure

- Create: `plugin/lib/caveman.sh` — `caveman_prefix` helper
- Modify: `plugin/plugin.json` — version → `0.9.0`
- Modify: `plugin/README.md` — acknowledgements section
- Modify: `plugin/skills/mvp-loop/SKILL.md` — caveman dispatch example
- Create: `tests/plan-9/test_polish.bats`

---

## Task 1: `caveman.sh` + SKILL.md update

**Files:** `plugin/lib/caveman.sh`, updated `mvp-loop` SKILL.md, `tests/plan-9/test_polish.bats`

- [ ] **Step 1: Write failing tests**
- [ ] **Step 2: Implement caveman.sh**
- [ ] **Step 3: Update SKILL.md with concrete dispatch example**
- [ ] **Step 4: Bump plugin.json + README acknowledgements**
- [ ] **Step 5: Run tests, expect PASS**
- [ ] **Step 6: Commit**

---

*End of Plan 9.*
