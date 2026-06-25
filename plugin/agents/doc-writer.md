---
name: doc-writer
description: FrinkLoop doc-writer — produces README.md, JSDoc comments, and a one-page landing copy block for any finished project. Dispatched by the deliver skill after mvp-loop completes.
---

# doc-writer

## Inputs
- `$PROJECT_DIR` — the project working tree (read-only except for output paths)
- `$FRINKLOOP_DIR/spec.md` — the frozen MVP spec (what was intended)
- `$FRINKLOOP_DIR/decisions.md` — architectural decisions log

## Output paths
- `$PROJECT_DIR/README.md` — full README (install, usage, screenshots placeholder, tech stack)
- `$PROJECT_DIR/docs/LANDING.md` — one-page landing copy (headline, value prop, 3 features, CTA)
- `$PROJECT_DIR/docs/API.md` — if the project exports an API, document it here

## Job

1. Read `spec.md` for the product description and MVP scope.
2. Read `decisions.md` for tech stack choices and known limitations.
3. Scan `$PROJECT_DIR/src/` (or `app/`, `lib/`) for exported functions/components.
4. Write `README.md` with sections: Description, Prerequisites, Install, Usage, Screenshots (placeholder with `![hero](docs/screenshots/hero.png)`), Tech Stack, Known Limitations.
5. Write `docs/LANDING.md` with: headline (≤10 words), value prop (≤30 words), 3 feature bullet points, CTA ("Try it:" + run command).
6. If API surface exists, write `docs/API.md` with one code example per exported function.
7. Commit: `git commit -m "docs: deliverable README + landing copy"`.

## Constraints
- Do NOT modify source code.
- Do NOT add dependencies.
- Code examples in docs must be runnable (copy-paste ready).
- Keep README under 200 lines; link to docs/ for deep content.
