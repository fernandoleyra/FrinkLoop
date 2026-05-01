# claude-default — components

This design system favors:
- A serif body font for warmth.
- Monochrome surfaces with one accent color used sparingly (a single CTA per page, badges, error/success states only).
- Generous vertical spacing (`lg` and `xl`) between content blocks.
- Tight horizontal rhythm using `md`.

## Conventions

- **Buttons** — Primary uses `accent`, on hover darken 8%. Secondary is transparent with `border`.
- **Inputs** — `border` outline; on focus, swap border to `accent`. No drop shadows.
- **Cards** — `bg` with `radii.md`, `shadows.sm`. Padding `lg`.
- **Headlines** — Use `typography.scale.3xl` for hero. `2xl` for section titles. Always `weights[2]` (600).
- **Body** — `weights[0]` (400), `scale.base`, `1.6` line-height.

## Anti-patterns

- No gradients.
- No emoji in copy unless explicit.
- Avoid `lg` shadows; reserve for modals only.
- Never combine multiple accent shades; one accent, full stop.
