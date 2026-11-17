# SignalFlow AI — Google-inspired product design system

## Product direction

SignalFlow AI uses a Google-inspired, Material 3-influenced interaction and visual language. This is an independent product identity; it does not use Google's logo, proprietary assets, or claim affiliation with Google.

The design language applies to the complete frontend experience: the application shell, overview, account list, account-management workflows, create-account forms, integration status, loading states, errors, empty states, and not-found routes. New routes must reuse the same tokens and component patterns rather than introducing a separate visual style.

## Foundations

### Color tokens

| Token | Light value | Intended use |
|---|---|---|
| Primary | `#1A73E8` | Primary actions, links, focus and active emphasis |
| Primary dark | `#1558B0` | Hover state |
| Primary container | `#E8F0FE` | Tonal actions and selected surfaces |
| Canvas | `#F8F9FA` | Application background |
| Surface | `#FFFFFF` | Workspace panels and cards |
| Container | `#F1F3F4` | Search and subtle controls |
| Hover | `#D3E3FD` | Selected navigation and hover surfaces |
| Outline | `#DADCE0` | Hairline separators and form outlines |
| Text | `#202124` | Primary content |
| Secondary text | `#5F6368` | Supporting content |
| Error | `#D93025` | Errors |
| Success | `#1E8E3E` | Successful operations |
| Warning | `#F9AB00` | Warnings |

### Typography

- Plus Jakarta Sans: product headings, navigation emphasis and selected numeric emphasis.
- Roboto: body text, data tables, forms and dense interface copy.
- Sentence case for user-facing labels.
- Restrained 400/500/600 weights; avoid excessive boldness.
- Maintain readable contrast and visible focus indicators.

### Layout and shape

- Spacing based on 4px increments and an 8px rhythm.
- 64px desktop top app bar.
- 256px desktop navigation drawer, collapsing to an off-canvas drawer on smaller screens.
- 56px companion rail on wide screens.
- Pill-shaped search and primary/tonal controls.
- 8–16px card and dialog radii.
- Hairline outlines instead of heavy resting shadows.

## Interaction standards

- All interactive elements require keyboard-operable behavior and visible focus.
- `/` focuses global search when focus is not already inside an editable field.
- `Escape` closes the account detail panel.
- Loading uses skeleton placeholders rather than a blocking full-screen spinner.
- Success feedback uses a transient snackbar; errors remain visible and actionable.
- Respect `prefers-reduced-motion`.
- Empty states explain the situation and offer a relevant next action.
- Responsive layouts must preserve access to all primary workflows.

## Component reuse rules

- Use the shared color and typography tokens in `frontend/app/globals.css`.
- Reuse the established button, icon-button, panel, form, table, alert, snackbar and skeleton classes.
- Route-level loading, error and not-found states must use the same visual language.
- Do not introduce arbitrary colors, heavy shadows, uppercase labels or unrelated radius scales.
- Do not create decorative controls that imply functionality which is not implemented.

## Accessibility and verification

- Use semantic headings, labels and button names.
- Keep focus visible and controls usable by keyboard.
- Check text and control contrast against WCAG AA targets (4.5:1 for normal text).
- Verify at desktop, tablet and mobile widths.
- Run `npm run typecheck` and `npm run build` after dependency installation; perform browser-based interaction and accessibility checks before release.
