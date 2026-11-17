## 0.3.1 — local run orchestration and frontend build hardening

- Added a one-shot, idempotent demo-seed service after successful database migrations; API startup now waits for seed completion.
- Moved public frontend API and demo-tenant configuration into Docker build arguments so Next.js receives values at build time.
- Added frontend production typecheck before the Next.js production build and a container health check.
- Added Windows PowerShell start, stop and status scripts with Docker readiness and API readiness checks.
- Corrected local-development instructions to use host-local PostgreSQL/Redis addresses rather than Docker Compose service DNS names.
- Verified backend suite: 29 passed, 1 optional live-PostgreSQL test skipped. Docker and npm build remain unverified in this environment.

# SignalFlow AI — release notes

## 0.3.0 — API contract hardening

- Strengthened request validation for company names, optional text, country codes, evidence URLs and timezone-aware signal timestamps.
- Reject duplicate company domains inside a single ingestion batch, including URL aliases after canonical normalization.
- Expanded account search to match company name, domain and industry, with SQL wildcard escaping.
- Added regression coverage for search behavior and invalid ingestion/signal payloads.
- Added HubSpot v3 signature headers to the browser CORS allowlist for explicitly configured webhook tooling.

## Final project package

### Implemented in this package

- FastAPI versioned account, signal, ingestion and prioritized-lead APIs.
- PostgreSQL schema and Alembic migrations, including forced row-level security and an idempotent webhook inbox.
- Tenant-scoped application queries and a composite database foreign key binding each buying signal to an account in the same tenant.
- HS256 bearer-token tenant validation outside local mode, including configured issuer/audience checks; local demo mode uses a synthetic tenant header.
- Automatic score recalculation when a buying signal is added.
- Audit records for account, signal, score, ingestion, research, CRM sync and webhook events.
- Native HubSpot v3 webhook signature verification in configured production mode, local HMAC test envelopes, and tenant-scoped event deduplication.
- Async HubSpot CRM company upsert adapter for a single configured private-app token.
- Optional OpenAI-compatible structured AI research over stored account context.
- Celery/Redis worker foundation.
- Next.js dashboard with prioritized accounts, search, refresh, account creation, buying-signal entry, AI research and CRM sync actions.
- Docker Compose stack, CI workflow, unit tests, operations/security/deployment/integration documentation.

### Explicitly not certified as production-ready

- No real production identity provider, login, SSO, MFA, RBAC or user administration.
- PostgreSQL RLS is implemented but has not been verified against a live PostgreSQL runtime role in this environment; run `tests/test_postgres_rls.py` with `TEST_POSTGRES_URL` before production.
- HubSpot OAuth and encrypted per-tenant token lifecycle are not implemented; configured private-app token mode is single-tenant only.
- Native HubSpot webhook validation is implemented, but production app-secret and portal-to-tenant configuration must be supplied and tested against your HubSpot app.
- AI research does not browse the web or independently validate claims or URLs.
- No cloud account infrastructure, managed secrets, TLS, WAF, rate limiting, monitoring deployment, restore drill or penetration test is provisioned.
- This environment did not have Docker, the PostgreSQL driver or Node project dependencies available, so a full Docker build, live PostgreSQL migration/RLS verification and Next.js production build could not be executed here. The backend unit/API integration suite ran on SQLite; the optional PostgreSQL test was skipped.

## Verification performed in the packaging environment

- Backend test suite: 29 passed, 1 skipped (the optional live PostgreSQL RLS test requires `TEST_POSTGRES_URL`).
- Python source compilation: passed.
- Docker Compose and GitHub Actions YAML parsing: passed.
- PostgreSQL init shell script syntax: passed.
- Frontend TypeScript/TSX syntax transpilation: passed.
- Docker image build, actual PostgreSQL migrations/RLS, npm dependency installation and Next.js production build: not run because Docker was unavailable and npm dependency installation timed out in the packaging environment.

Use the deployment checklist and security document as mandatory go-live gates. Do not load real customer data until those items are completed and reviewed.

