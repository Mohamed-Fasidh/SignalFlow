# SignalFlow AI — Material Design 3 implementation

SignalFlow AI is an independent product. Its interface takes inspiration from Material Design 3 and familiar productivity-workspace patterns; it is not affiliated with Google and does not use Google Workspace branding or logos.

## Implemented in this revision

- Cool off-white application canvas and white rounded workspace surface, with hairline borders and restrained elevation.
- Google-blue light theme and charcoal/periwinkle dark theme, with the theme preference persisted locally.
- Plus Jakarta Sans headings, Roboto interface typography, and Material Symbols Outlined icon font.
- Sentence-case UI labels, restrained 400/500 typography, compact data rows, 8px control corners and 4px snackbar corners.
- 64px sticky app bar, universal account search, inline high-intent filter, autocomplete results, support/settings/app launcher/profile actions, 256px navigation drawer and 72px collapsed desktop rail.
- Pointer-coordinate state-layer/ripple treatment, decelerated easing, reduced-motion support and visible keyboard focus. Account creation and buying-signal submission use optimistic local updates with rollback on request failure.
- Skeleton loading states, a no-results state, error boundary, offline banner, local notes/task persistence, and an offline request queue for account creation and buying-signal creation. Queued requests retry when the browser reports connectivity.
- Keyboard shortcuts: `/` search, `Esc` dismiss, `j`/`k` or arrow keys move through account rows, `x` select the focused account, and `?` open shortcut help. Utility panels trap keyboard focus.
- Account list pagination (100 rows per request) and client-side windowing (30 visible rows with overscan) to avoid rendering every loaded row at once.

## Important implementation boundaries

- The API exposes a maximum page size of 100 for prioritized leads. The UI fetches subsequent pages as the user scrolls; it does not fetch 10,000 rows at startup. The list windowing is implemented without adding a third-party virtualization dependency.
- Offline queueing covers the two supported create operations (accounts and buying signals). It is stored in browser local storage, is device/browser-local, and is not an encrypted durable sync engine. Do not use it for sensitive data on shared devices.
- Notes and the demo task are browser-local conveniences, not server-backed collaboration features.
- Material Symbols and web fonts are fetched from Google Fonts. System fallbacks remain available when offline; the first uncached visit while offline will use fallbacks.
- The design uses a Google-inspired four-color avatar ring as a generic workspace affordance only. SignalFlow AI is not a Google product.

## Verification status

- Backend test suite: 29 passed, 1 skipped.
- TypeScript/TSX transpilation: all five app TSX files passed syntax transpilation.
- Full Next.js typecheck/production build: not verified because dependency installation timed out in this environment.
- Browser-based interaction, screen-reader testing, Lighthouse/Core Web Vitals, measured input latency, and 10,000-record load testing: not performed. Do not interpret the target thresholds in the product brief as measured results.
- Docker/PostgreSQL runtime and external integration tests remain separate deployment checks.
