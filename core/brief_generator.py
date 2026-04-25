"""
core/brief_generator.py — Generate comprehensive BRIEF.md from structured questions

Takes user answers and expands them via LLM into a professional specification
matching the quality of V1 briefs (hearsh, firecrawl-clone, etc.)

Features:
- Intuitive selector-based UI for quick input
- Conversational refinement loop if user rejects brief
- LLM thinks like a VC and proposes ambitious success criteria
"""

from core.llm import call_llm


def _show_selector(label: str, options: list[str]) -> str:
    """Show a menu and return selected option."""
    print(f"\n{label}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    
    while True:
        try:
            choice = input(f"  ? Select (1-{len(options)}) [1] ").strip() or "1"
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, IndexError):
            pass
        print(f"  Invalid. Choose 1-{len(options)}.")



def gather_brief_questionnaire(prompt_fn, prompt_multiline_fn, prompt_list_fn) -> dict[str, str]:
    """Interactive questionnaire with smart defaults and selectors."""

    print("\n" + "=" * 70)
    print("  BRIEF QUESTIONNAIRE — Quick Setup")
    print("=" * 70)
    print("\n(Use selectors for quick defaults, or type custom answers.)\n")

    # 1. What kind of project?
    project_type = _show_selector(
        "1. What are you building?",
        [
            "CLI tool (command-line utility)",
            "REST API / Backend service",
            "Web app (frontend)",
            "Mobile app",
            "Library / SDK",
            "Data pipeline / ETL",
            "Other (I'll describe it)",
        ],
    )

    if project_type == "Other (I'll describe it)":
        raw_idea = prompt_multiline_fn("   Describe your idea:")
    else:
        raw_idea = project_type

    # 2. Problem it solves
    print("\n2. What problem does it solve? (1-2 sentences, or leave blank for LLM to guess)")
    problem = prompt_multiline_fn(
        "  Enter answer (blank line to skip):",
        allow_empty=True
    )
    if not problem.strip():
        problem = "(Let LLM infer from project type)"

    # 3. Core features (or quick templates)
    print("\n3. Core features:")
    use_template = _show_selector(
        "   Use a template or custom?",
        ["Quick template (auto-generate)", "Type custom features", "Skip (LLM decides)"],
    )

    features = ""
    if use_template == "Quick template (auto-generate)":
        features = f"(Auto-generate typical features for a {project_type})"
    elif use_template == "Type custom features":
        features_list = prompt_list_fn("   Features (one per line, blank to finish)")
        features = "\n".join(f"- {f}" for f in features_list) if features_list else "(none specified)"
    else:
        features = "(LLM will propose)"

    # 4. Tech constraints / preferences
    print("\n4. Tech preferences:")
    tech_choice = _show_selector(
        "   Infrastructure preference?",
        [
            "Local/offline first (no cloud)",
            "Cloud-native (AWS/GCP/Azure)",
            "Self-hosted (your own servers)",
            "No preference (LLM decides)",
        ],

    )

    constraints = prompt_multiline_fn(
        "   Other constraints? (budget, compliance, performance, leave blank if none)",
        allow_empty=True
    )
    if not constraints.strip():
        constraints = tech_choice
    else:
        constraints = f"{tech_choice}; {constraints}"

    return {
        "raw_idea": raw_idea,
        "problem": problem,
        "features": features,
        "constraints": constraints,
    }


def expand_brief_with_llm(project_name: str, answers: dict[str, str]) -> str:
    """
    Send raw user answers to LLM and get back a comprehensive BRIEF.md.
    
    The LLM thinks like a VC/CEO and:
    - Proposes ambitious success metrics
    - Fleshes out the spec into a ship-ready design
    - Suggests the best tech stack and architecture
    - Makes it concrete and measurable
    """

    system_prompt = """You are a visionary CEO and seasoned VC investor evaluating a startup idea.
Your job is to take a vague user idea and expand it into a comprehensive, ambitious BRIEF.md.

Think like a moonshot founder. Propose:
1. **Clear problem statement** — what pain point you're solving
2. **Target users & market** — who wins from this
3. **Ambitious success criteria** — specific, measurable KPIs a VC would demand
4. **Core features** — polished version of what user suggested + what's missing
5. **API/Interface** — exact endpoints, commands, or SDK methods
6. **Tech stack** — with rationale for each choice
7. **Project structure** — directory layout ready to build
8. **Why this matters** — market opportunity and differentiation

You are not overthinking. You are SHIPPING.
Be specific. No vague language. Show code examples, API specs, metrics.

Reference real examples:
- For a CLI tool: show exact commands, exit codes, output format
- For an API: show ALL endpoints with parameters and response schemas
- For a library: show import syntax, class definitions, method signatures
- For success: show exact metrics (latency <X ms, throughput >Y req/s, >Z% adoption, etc.)

Write the complete BRIEF.md. Start with markdown directly (no preamble)."""

    user_prompt = f"""Expand this raw idea into a comprehensive BRIEF.md.
The user has given a vague idea and you must:
1. Clarify the problem they're solving
2. Propose ambitious, measurable success criteria
3. Flesh out the spec they gave
4. Make it ship-ready

User's raw idea:
{answers['raw_idea']}

Problem they see:
{answers['problem']}

Features they mentioned:
{answers['features']}

Constraints:
{answers['constraints']}

Now write a professional BRIEF.md as if you're pitching this to a VC.
Include everything a developer needs to build it without asking questions.
Make success criteria concrete and measurable (e.g., "<500ms p99 latency", ">90% accuracy", "ships in 2 weeks")."""

    brief_md = call_llm(system_prompt, user_prompt, max_tokens=4096)
    return brief_md.strip()


def show_brief_and_approve(brief_md: str, project_name: str, confirm_fn) -> bool:
    """
    Display LLM's vision/proposal to user for approval.
    Returns True if approved, False if rejected or needs revision.
    """

    print("\n" + "=" * 70)
    print(f"  VC VISION — {project_name}")
    print("=" * 70)
    print("  This is the LLM's proposal for what you should build.")
    print("  It includes ambitious success metrics and concrete specs.\n")

    print(brief_md)

    print("\n" + "=" * 70)
    approved = confirm_fn("Is this the vision you want to ship?", default=True)
    return approved


def conversational_refinement_loop(
    project_name: str,
    brief_md: str,
    answers: dict[str, str],
    prompt_fn,
    confirm_fn,
) -> str:
    """
    If user rejects brief, enter a conversational loop to refine it.
    Continues for at least 5 exchanges until user approves.
    """
    print("\n" + "=" * 70)
    print("  REFINEMENT LOOP — Let's improve it together")
    print("=" * 70 + "\n")

    iteration = 0
    max_iterations = 10  # Allow up to 10 refinement rounds
    feedback_history = []

    while iteration < max_iterations:
        iteration += 1
        print(f"\n[Round {iteration}] What would you like to change?\n")
        print("  Examples:")
        print("    - Focus more on performance")
        print("    - Make it more ambitious")
        print("    - Different tech stack")
        print("    - Simpler first version")
        print("    - Add [specific feature]")
        print("    - Remove [feature]")

        feedback = prompt_fn("Your feedback").strip()
        if not feedback:
            print("  (No feedback entered.)")
            continue

        feedback_history.append(feedback)

        print(f"\n  ✓ Refining brief based on: {feedback[:60]}...")

        # Re-generate with refined context
        brief_md = _refine_brief_with_feedback(
            project_name,
            answers,
            brief_md,
            feedback_history,
        )

        # Show refined version
        print("\n" + "-" * 70)
        print(brief_md)
        print("-" * 70)

        # Ask again
        approved = confirm_fn("Better now?", default=True)
        if approved:
            print("\n  ✓ Brief locked in!")
            return brief_md

        # Encourage continuing if not enough iterations yet
        if iteration < 5:
            print("  (Let's keep refining...)\n")

    print("\n⚠ Reached max refinement rounds. Using current version.")
    return brief_md


def _refine_brief_with_feedback(
    project_name: str,
    answers: dict[str, str],
    current_brief: str,
    feedback_history: list[str],
) -> str:
    """Re-generate brief incorporating user feedback."""

    system_prompt = """You are a visionary CEO and seasoned VC investor refining a startup brief.
The user has given feedback on the current brief. Your job is to:
1. Incorporate their feedback into the spec
2. Keep the ambitious vision
3. Make it ship-ready with concrete metrics

Do NOT soften the brief unnecessarily. Push back on vague feedback by making it more concrete.
If they say "simpler", propose a clear MVP scope. If they say "more ambitious", push metrics harder.

Write the complete refined BRIEF.md. Start with markdown directly."""

    feedback_str = "\n".join(f"- {f}" for f in feedback_history)

    user_prompt = f"""Refine this BRIEF.md based on user feedback.

Original idea:
{answers['raw_idea']}

Current brief:
---
{current_brief}
---

User feedback (in order):
{feedback_str}

Incorporate their feedback and re-generate the BRIEF.md.
Keep it ambitious and specific. Use concrete metrics."""

    refined = call_llm(system_prompt, user_prompt, max_tokens=4096)
    return refined.strip()


def generate_brief_interactive(project_name: str, prompt_fn, prompt_multiline_fn, prompt_list_fn, confirm_fn) -> tuple[str, dict]:
    """
    Full pipeline: questionnaire → LLM expansion → approval or refinement loop.

    Returns (brief_md, answers) so the caller can use answers (e.g. raw_idea)
    for template selection without re-parsing the brief.
    """
    print(f"\nGenerating comprehensive BRIEF for {project_name}...")
    print("Quick setup → LLM vision → ship it!\n")

    answers = gather_brief_questionnaire(prompt_fn, prompt_multiline_fn, prompt_list_fn)

    print("\n  ✓ LLM is thinking like a VC...\n")
    brief_md = expand_brief_with_llm(project_name, answers)

    approved = show_brief_and_approve(brief_md, project_name, confirm_fn)

    if not approved:
        brief_md = conversational_refinement_loop(
            project_name,
            brief_md,
            answers,
            prompt_fn,
            confirm_fn,
        )

    return brief_md, answers
