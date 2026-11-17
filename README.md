# SignalFlow AI

**GTM intelligence, explainable lead scoring, enrichment pipelines and CRM-ready automation.**

SignalFlow AI is a production-oriented starter platform for sales and GTM engineering teams. It ingests company records, normalizes and deduplicates them, stores evidence-backed buying signals, computes explainable scores, and exposes prioritized accounts through a versioned API.

> **Release status:** This is a feature-complete local development/demo release with tested core API workflows. It is **not production-certified**. Cloud infrastructure, external identity-provider integration and user RBAC, multi-tenant CRM OAuth/token vaulting, source-backed web research, and live staging/production validation still require environment-specific work.

## Included

- FastAPI backend with versioned REST endpoints and OpenAPI docs
- PostgreSQL data model and Alembic migrations
- SQLAlchemy persistence, tenant-aware account records, and audit events
- Explainable deterministic lead scoring with freshness-aware evidence
- Idempotent ingestion endpoint, canonical domain deduplication, and preflight batch validation
- Strict API request validation for evidence URLs, UTC-aware timestamps, country codes, and bounded text fields
- Redis + Celery background task scaffold and scheduled task entry point
- Native HubSpot v3 webhook signature verification and replay-safe event inbox
- Async HubSpot CRM v3 company upsert adapter (single-tenant private-app token mode; OAuth lifecycle remains future work)
- Celery-backed OpenAI-compatible structured research jobs with tenant-scoped persisted status/results (analyzes stored account context; does not browse or verify sources)
- Local generic HMAC webhook envelope endpoint; production mode requires native HubSpot v3 verification
- Signed HS256 bearer-token tenant validation outside local mode; PostgreSQL RLS policies add a second tenant-isolation layer
- Composite database foreign key prevents a signal from referencing an account owned by another tenant
- PostgreSQL row-level security policies on accounts, signals, audit events, webhook inbox, and research jobs
- Transaction-local tenant context set on every request transaction
- Webhook inbox with a tenant/provider/event uniqueness constraint to prevent duplicate processing
- Docker Compose local stack with separate admin, migration-owner, and restricted runtime database roles, health checks, and environment configuration
- Pytest tests, Ruff, mypy configuration, and GitHub Actions CI
- Next.js dashboard for account prioritization, account creation, buying-signal capture, research, and CRM actions
- Compose startup orchestration: migrations → idempotent demo seed → API → worker → frontend
- Windows PowerShell start/stop/status scripts
- Deployment, security, backup, monitoring, and runbook documentation

## Architecture

```text
External sources / CSV / CRM webhooks
              |
        FastAPI ingestion API
              |
      validation + normalization
              |
    PostgreSQL (accounts, signals,
    jobs, audit, tenant ownership)
              |
       Celery + Redis workers
              |
   scoring / enrichment / CRM adapter
              |
      prioritized-account API
              |
        Next.js dashboard
```

PostgreSQL is the system of record. Redis is a queue/cache, not a source of truth. Background jobs must be idempotent. External content is treated as untrusted input. AI output is advisory and requires human review before external actions.

## Quick start (Docker)

**Requirements:** Docker Desktop / Docker Engine with the Compose plugin.

### Windows (PowerShell)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\start.ps1
```

### macOS / Linux

```bash
cp .env.example .env
# Change SECRET_KEY and WEBHOOK_SIGNING_SECRET before exposing any service.
docker compose up --build -d
docker compose ps
```

The stack automatically runs database migrations and inserts one clearly labelled synthetic demo account before starting the API. You do not need to run a separate seed command for a fresh local environment. To inspect startup failures, run:

```bash
docker compose logs --tail=150
```

Then open:

- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/health/live
- Dashboard: http://localhost:3000

The demo tenant ID is `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa`. Demo records are synthetic and are seeded automatically. The seed command is safe to rerun.

Use the tenant ID in the `X-Tenant-ID` header for local API requests. Example:

```bash
curl -H "X-Tenant-ID: <tenant-uuid>" http://localhost:8000/api/v1/accounts
```

## Run automated checks

```bash
cd backend
pip install -e ".[dev]"
pytest -q
ruff check app tests
```

The standard test suite runs API integration tests on SQLite for fast feedback. Set `TEST_POSTGRES_URL` to a migrated PostgreSQL test database using a non-superuser, non-`BYPASSRLS` runtime role to enable the optional PostgreSQL RLS integration test.

## Local development without Docker

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install dependencies and configure the environment:

```bash
pip install -e ".[dev]"
```

```powershell
# Windows PowerShell: copy the root environment template
Copy-Item ..\.env.example ..\.env
```

```bash
# macOS / Linux
cp ../.env.example ../.env
```

After configuring a local PostgreSQL and Redis instance and setting `DATABASE_URL` and `REDIS_URL` in `.env`, run:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | PostgreSQL and Redis readiness |
| POST | `/api/v1/accounts` | Create account |
| GET | `/api/v1/accounts` | List/search accounts by company name, domain, or industry |
| GET | `/api/v1/accounts/{id}` | Account details |
| POST | `/api/v1/signals` | Record a buying signal |
| POST | `/api/v1/accounts/{id}/score` | Recalculate score |
| GET | `/api/v1/accounts/{id}/signals` | List account signals |
| POST | `/api/v1/accounts/{id}/research` | Queue an AI research job via Celery |
| GET | `/api/v1/research/jobs` | List tenant-owned research jobs |
| GET | `/api/v1/research/jobs/{job_id}` | Read tenant-scoped research status and result |
| GET | `/api/v1/audit/events` | Tenant audit history |
| GET | `/api/v1/webhooks/events` | Webhook inbox and JSON payloads |
| GET | `/api/v1/integrations/hubspot/status` | HubSpot configuration and latest webhook status |
| GET | `/api/v1/duplicates` | Heuristic duplicate candidates |
| POST | `/api/v1/accounts/{source_id}/merge/{target_id}` | Merge duplicate account and transfer signals |
| PATCH | `/api/v1/signals/{signal_id}/archive` | Archive a buying signal and rescore |
| PATCH | `/api/v1/signals/{signal_id}/restore` | Restore an archived buying signal |
| PATCH | `/api/v1/accounts/{account_id}/priority` | Set account priority |
| POST | `/api/v1/accounts/{account_id}/hubspot-note` | Push a note to HubSpot (demo tenant only) |
| POST | `/api/v1/accounts/{id}/hubspot-sync` | Sync company to configured HubSpot |
| GET | `/api/v1/leads/prioritized` | Ranked accounts |
| POST | `/api/v1/ingestion/accounts` | Idempotent bulk ingestion |
| POST | `/api/v1/webhooks/hubspot` | Verify native HubSpot v3 signatures in production; local generic HMAC envelope for development |

In local mode, tenant-scoped endpoints use `X-Tenant-ID` for the synthetic demo tenant. In other modes, endpoints require a signed bearer JWT containing `tenant_id`, `iat`, and `exp`. PostgreSQL RLS is enforced by migrations; the application database role must not be a superuser or have `BYPASSRLS`. Configure a trusted identity provider to issue tokens; the repository does not include user login, token issuance, user-level RBAC, or SSO. See [docs/SECURITY.md](docs/SECURITY.md) and [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

### Production identity configuration

Set `JWT_ISSUER` and `JWT_AUDIENCE` to the exact values issued for the SignalFlow API. Production startup refuses to start without them, and bearer tokens with a mismatched issuer or audience are rejected. The application does not issue user tokens or replace an identity provider; configure tenant membership and roles at the identity layer.

## Scoring model

The score is deterministic and explainable. Default weights:

- Explicit compliance requirement: +25
- Security/compliance hiring: +20
- Enterprise expansion: +20
- Recent funding: +15
- ICP company-size fit: +10

Scores are capped at 100. Each score response includes reasons and signal IDs. Scores are recalculated automatically when a signal is created, and can also be recalculated explicitly. Tune weights against labeled outcomes; do not represent this as a statistically validated propensity model until trained and evaluated.

## Dashboard design system

The dashboard uses a Google-inspired Material 3 visual language: Google blue primary actions, tonal surfaces, Roboto body typography, restrained Google Sans headings, sentence-case labels, rounded controls, hairline dividers, responsive navigation, skeleton loading, keyboard search (`/`), Escape-to-close behavior, accessible labels, and transient snackbars.

The visual language is inspired by Google's public product design patterns. SignalFlow AI is an independent brand and is not an official Google product or an exact reproduction of proprietary Google UI assets.

### Dashboard interactions

Help, Settings, Apps, Calendar, Notes, Tasks, and Contacts open contextual panels. External-provider-dependent features are labelled as not connected; Notes and Tasks are local demo state only.

See [docs/MATERIAL_DESIGN_3_IMPLEMENTATION.md](docs/MATERIAL_DESIGN_3_IMPLEMENTATION.md) for design tokens, interaction patterns, offline behavior, pagination/windowing, and verification limitations.

## Workspace operations API

The dashboard's operational views are backed by tenant-scoped endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/integrations/hubspot/status` | Demo connection configuration and latest accepted webhook |
| GET | `/api/v1/webhooks/events` | Webhook inbox with JSON payloads |
| GET | `/api/v1/audit/events` | Tenant audit history |
| GET | `/api/v1/duplicates` | Heuristic duplicate candidates (maximum 1,000 scanned accounts) |
| POST | `/api/v1/accounts/{source_id}/merge/{target_id}` | Move signals to target and merge duplicate account |
| PATCH | `/api/v1/signals/{signal_id}/archive` | Undoable signal archive operation |
| PATCH | `/api/v1/signals/{signal_id}/restore` | Restore an archived signal and rescore |
| PATCH | `/api/v1/accounts/{account_id}/priority` | Update account priority |
| POST | `/api/v1/accounts/{account_id}/hubspot-note` | Create and associate a HubSpot note (configured demo tenant only) |
| POST | `/api/v1/accounts/{account_id}/research` | Queue an AI research job in Celery |
| GET | `/api/v1/research/jobs/{job_id}` | Read tenant-owned research job state and result |

Apply all Alembic migrations with `alembic upgrade head` before running the updated API. AI research requires a running Redis broker and Celery worker. See [docs/WORKSPACE_SHELL_POLISH.md](docs/WORKSPACE_SHELL_POLISH.md) for implementation details and verification limits.

## Project layout

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # HTTP routes and schemas
│   │   ├── core/         # settings, database, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # scoring, ingestion
│   │   ├── integrations/ # CRM and AI boundaries
│   │   ├── workers/      # Celery tasks
│   │   └── scripts/
│   ├── alembic/
│   └── tests/
├── frontend/             # Next.js dashboard
├── infra/                # deployment and observability examples
├── docs/                 # runbooks and design docs
├── .github/workflows/
└── docker-compose.yml
```

## Production deployment checklist

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). The Docker Compose stack is for local development and demo validation. Before production:

1. Use managed PostgreSQL and Redis in private networking.
2. Configure TLS, a real identity provider, RBAC, and tenant isolation tests.
3. Store secrets in AWS Secrets Manager / Parameter Store, never in Git.
4. Run migrations as a one-off release task.
5. Deploy API and worker as separate services.
6. Configure backups, restore drills, metrics, alerts, and log retention.
7. Configure real CRM OAuth, scopes, webhook subscriptions, and token refresh.
8. Complete privacy/legal review for data sources, retention, and outreach rules.
9. Load test, threat model, and penetration test the deployed environment.

## Security notes

- Never commit `.env`, API keys, OAuth tokens, production data, or PII.
- Use a dedicated service identity and least-privilege database credentials.
- Validate webhook signatures against the exact raw request body.
- Apply provider-specific consent/lawful-basis and suppression rules before outreach.
- Do not let an LLM send messages, modify CRM records, or make irreversible changes without approval.
- Rotate all credentials immediately if exposed.

## License

MIT for this starter implementation. Review third-party service terms and data rights independently.

## Further documentation

- [Deployment guide](docs/DEPLOYMENT.md)
- [Security guide](docs/SECURITY.md)
- [Integration notes](docs/INTEGRATIONS.md)
- [Material Design 3 implementation](docs/MATERIAL_DESIGN_3_IMPLEMENTATION.md)
- [Workspace shell polish](docs/WORKSPACE_SHELL_POLISH.md)
- [Final implementation status](docs/FINAL_IMPLEMENTATION_STATUS.md)
