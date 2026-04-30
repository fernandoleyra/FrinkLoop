---
name: intake-chat
description: FrinkLoop intake chat — a 9-step YC-shaped clarifier that turns a project idea into a frozen spec.md and config.yaml. Run with compression off (user-facing). Output goes to <project>/.frinkloop/.
---

# intake-chat

Run a structured 9-step conversation with the user to produce a frozen spec.md and config.yaml.

## Compression

Always run with caveman compression **off** during this skill — output is user-facing and needs natural prose.

## Steps (one question per turn)

### 1. YC pitch (4 sub-questions)

Ask in order, one per turn:
- "What does it do?" — capture as `pitch_does` (1 sentence).
- "Who is this for? Be specific." — capture as `pitch_for`.
- "What's the smallest version that proves it works?" — capture as `pitch_proves`.
- "What would make a user say 'I want this'?" — capture as `pitch_makes_them_say`.

### 2. Mode

Ask: "Hackathon demo, Commercial MVP, or Internal demo?" — capture as `mode` ∈ {hackathon, commercial, internal-demo}.

### 3. HITL level

Ask: "How human-in-the-loop? Fully autonomous, milestone checkpoints, or flag-on-blocker only?" — capture as `hitl`.

### 4. Platform & deploy target

Auto-suggest from the pitch (use the platform → registry mapping in `plugin/templates/registry.yaml`). Ask user to confirm or override. Capture as `platform` and `deploy_target`.

### 5. Stack preference

Ask: "Pick a recipe yourself, or shall I use the default for `<platform>`?"
- "I pick" → list options from `registry.yaml`, capture choice as `template`.
- "You choose" → use registry default for that platform.

### 6. Design system

List local design systems under `~/.claude/plugins/frinkloop/design-systems/` plus the built-in `claude-default`. Offer:
- *Use existing* (pick by name) → capture name
- *Clone URL or brand* → defer to `design-system-builder` (Plan 5; for Plan 1, fall back to `claude-default` and note in decisions.md)
- *Create new* → defer to `design-system-builder` (same Plan 1 fallback)
- *Use stack default* → "tailwind-shadcn-defaults"

### 7. Hard exclusions

State: "By default, FrinkLoop excludes from MVP: real auth, payments, real user data, production observability, custom infra. Anything to add or remove?"

User can append. With explicit warning, can remove. Final list goes to `exclusions`.

### 8. Spec proposal

Synthesize: produce a draft of done-criteria (3–5 testable bullets derived from `pitch_proves` + `pitch_makes_them_say`), in-MVP bullets, and phase-2 bullets (= exclusions + ambitious-but-not-needed items). Present to user as a proposal. Edit inline based on user feedback.

### 9. Final approve

When user says "go", invoke the renderer:

```bash
plugin/skills/intake-chat/lib/render.sh /tmp/frinkloop-answers-$$.json "$PROJECT_DIR/.frinkloop"
```

Where the answers JSON has all captured fields:

```json
{
  "project": "...",
  "pitch_does": "...",
  "pitch_for": "...",
  "pitch_proves": "...",
  "pitch_makes_them_say": "...",
  "mode": "...",
  "hitl": "...",
  "compression": "full",
  "platform": "...",
  "template": "...",
  "design_system": "...",
  "deploy_target": "...",
  "tdd": false,
  "exclusions": ["..."],
  "done_criteria": ["...", "..."],
  "in_mvp": ["...", "..."]
}
```

After render succeeds:
- For Plan 1: stop here. Tell the user: "Spec written to `<project>/.frinkloop/spec.md` and config to `<project>/.frinkloop/config.yaml`. The build loop arrives in Plan 2."
- For Plan 2 onward: hand off to `mvp-loop` skill.

## Pre-fill from learning profile

If `~/.claude/plugins/frinkloop/learning/profile.json` exists, pre-fill defaults:
- `preferred_hitl` → default for step 3
- `preferred_stacks[<platform>]` → default for step 5
- `default_exclusions_added` → suggested adds at step 7
- `design_system_default` → default for step 6

(Implemented in Plan 6; for Plan 1, skip this section.)
