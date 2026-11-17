# SignalFlow AI workspace shell polish

## Implemented in this pass

- Reworked the top bar to use the 64px canvas-colored shell, geometric SignalFlow mark, universal search, filter-chip affordances, shortcut entry point, theme/settings controls, workspace avatar, and an explicitly truthful HubSpot setup status.
- Added debounced company suggestions backed by the existing tenant-scoped `GET /api/v1/accounts?q=...` PostgreSQL endpoint.
- Reorganized navigation around Priority accounts, Buying signals, AI research briefs, Duplicate & merge queue, CRM & integrations, and Audit logs. Counts shown beside Buying signals are the currently loaded signal-reason count, not an unread count.
- Added bulk selection and compact/comfortable density controls.
- Changed default virtualized account rows to 48px and aligned virtual spacer calculations with the selected density.
- Replaced the score gauge with tonal score pills and made row actions appear on hover/focus.
- Moved selected-account details into a 360px right-side panel with structured research sections, evidence-backed score reasons, copy, regenerate, and HubSpot-note action affordances.
- Added a slim progress indicator while account actions are in flight.
- Added semantic Material color tokens and dark-theme surfaces, plus `next/font/google` declarations for Plus Jakarta Sans, Roboto, and Roboto Mono.

## Existing capabilities retained

- FastAPI-backed account loading, creation, buying-signal submission, scoring, AI research request, and HubSpot company sync.
- Keyboard shortcuts `/`, `?`, `j`/`k`, `x`, `Enter`, and `Escape`.
- Local offline queue for supported account/signal creation flows, online replay, snackbar feedback, and theme persistence.

## Explicitly not represented as complete

- HubSpot webhook health/last-delivery status is not exposed by a health endpoint; the UI therefore says setup required rather than inventing a green connected state.
- CRM-synced and enterprise-tier filters require corresponding account/provider fields and are currently visual filter affordances, not verified server-side filters.
- Celery task lifecycle/progress is not wired to a task-status endpoint. The progress line indicates an active dashboard request only; it does not claim to measure queue depth or worker execution.
- Audit log and webhook delivery/payload inspection screens, duplicate merge workflow, unread signal state, HubSpot note creation, and real-time streaming research are not implemented in this pass.
- The current research provider summarizes supplied company context only; it does not browse or verify external sources.
- Google fonts require network access during the Next.js build unless the fonts are downloaded and self-hosted. A full production build was not run in this environment because frontend dependencies are not installed.

## Validation

- Backend tests: 29 passed, 1 skipped.
- TypeScript/TSX transpilation syntax check: 5 application files passed with zero syntax diagnostics.
- Full `next build`, browser interaction tests, Docker end-to-end validation, and live PostgreSQL/RLS validation remain outstanding.

## Backend-connected features added after the initial shell pass

- Explicit account `tier` (`unknown`, `smb`, `mid_market`, `enterprise`) and `crm_synced_at` fields, with tenant-scoped server-side filters on account search and prioritized leads.
- HubSpot status endpoint reports whether the demo private-app connection and native webhook secret are configured, plus the last accepted webhook timestamp/event ID.
- Tenant-scoped audit event and webhook delivery list endpoints, including JSON payload inspection in the UI.
- Duplicate candidate detection (bounded to the first 1,000 tenant accounts) and an explicit merge operation that moves source buying signals to the target before deleting the source. Merge requires a browser confirmation and is audited.
- Buying-signal archive and restore endpoints, score recalculation, audit events, optimistic UI update and a working snackbar Undo action.
- Account priority mutation (`low`, `normal`, `high`, `critical`) and pin/unpin actions with optimistic UI updates and audit history. Pinned accounts sort ahead of score-ranked accounts.
- HubSpot note creation and company association endpoint, gated by the explicitly configured demo tenant token.
- AI research is queued through Celery, persisted in `research_jobs`, listed in the research briefs view, and polled through tenant-scoped job endpoints. The worker persists structured results and failure state; the dashboard shows queue status while polling.
- Database migrations `0003_workspace_features`, `0004_account_filters`, and `0005_research_jobs` add the new fields and RLS-protected research job table.

## Current verification and limits

- Backend tests: **34 passed, 1 skipped**. The skipped test is the PostgreSQL-only RLS integration check.
- Python bytecode compilation: passed.
- TypeScript/TSX transpilation syntax check: passed for all five app TSX files. This is a syntax check, not a full dependency-aware typecheck.
- CSS brace-balance check: passed.
- `npm install` did not complete in this environment, so `next build` and browser E2E tests could not be run here. The Next.js production build remains a required local/CI verification step.
- Docker Compose, PostgreSQL migrations/RLS, Redis/Celery worker execution, live OpenAI-compatible research, and live HubSpot API calls were not run in this environment. They require Docker/services and valid external credentials.
- The duplicate review is heuristic (name similarity/domain-root), capped at 1,000 records, and must be reviewed by a human before merge. It is not an authoritative entity-resolution engine.
- HubSpot still uses a single explicitly allowlisted private-app token for the demo tenant. Multi-tenant OAuth, encrypted token vault/rotation, production user provisioning, MFA/SSO/RBAC, cloud deployment, monitoring, backup/restore drills, load testing and penetration testing remain outside this code-only completion pass.
- AI research analyzes stored account context only; it does not crawl the web or validate external facts. Treat generated content as an assistive draft, not verified market intelligence.
