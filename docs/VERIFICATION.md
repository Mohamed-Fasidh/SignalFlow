# Verification record

This record describes checks executed while preparing the downloadable package. It does not replace validation in the user's Docker/PostgreSQL/HubSpot/cloud environment.

## Passed

- Backend unit and API integration tests on SQLite: **29 passed**.
- Python source compilation: passed.
- Docker Compose and GitHub Actions workflow YAML parsing: passed.
- Compose startup dependency graph inspected: migrations → idempotent demo seed → API → worker/frontend.
- Windows PowerShell startup, stop and status scripts added; they require validation on a Windows host.
- PostgreSQL initialization shell script syntax (`sh -n`): passed.
- Frontend TypeScript/TSX syntax transpilation: passed for all five app TSX files (syntax transpilation only).
- Dashboard utility controls now open functional Help, Settings, Apps, Calendar, Notes, Tasks and Contacts panels; unsupported integrations are explicitly described as not yet connected.
- Backend tests rerun after the UI work: **29 passed, 1 skipped**.
- ZIP integrity: checked after packaging.

## Not executed in this environment

- PostgreSQL migration execution and RLS isolation test. The optional `backend/tests/test_postgres_rls.py` is skipped unless `TEST_POSTGRES_URL` points to a migrated PostgreSQL database accessed with a non-superuser runtime role that has no `BYPASSRLS` privilege.
- Docker image build and `docker compose up`, because Docker is not available in the packaging environment.
- Next.js dependency installation timed out in this environment. A direct `tsc --noEmit` attempt consequently failed because Next.js/React packages and their type declarations are not installed; this is an environment/dependency limitation, not a successful typecheck. The Dockerfile runs typecheck and production build during image creation, but those steps still need to be run on a machine with registry access.
- Live HubSpot API requests and native webhook delivery, because no HubSpot app credentials or portal mapping were provided.
- Live AI provider requests, because no AI API credentials were provided.
- Cloud deployment, TLS, managed secret storage, external OIDC/RBAC, monitoring and load/security testing.

## Before real customer data

Follow `SECURITY.md`, `DEPLOYMENT.md` and `INTEGRATIONS.md`. In particular, configure a trusted identity provider, validate issuer/audience and tenant membership, use a non-superuser database runtime role, run the PostgreSQL RLS test, complete HubSpot OAuth for multi-customer installations, and deploy to a secured staging environment before production.
