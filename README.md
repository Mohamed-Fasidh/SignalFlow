# SignalFlow AI

GTM intelligence, explainable lead scoring, enrichment pipelines and CRM-ready automation.

This repository contains the SignalFlow AI workspace, FastAPI backend, PostgreSQL/Alembic persistence, Redis/Celery background jobs, Next.js dashboard, Docker Compose development stack, tests, CI workflow, and operational documentation.

## Status

This is a production-oriented local development/demo release, not a production-certified deployment. External identity-provider integration, user RBAC/SSO, multi-tenant CRM OAuth/token lifecycle, source-backed web research, and live staging/production validation require environment-specific configuration and verification.

## Quick start

1. Copy `.env.example` to `.env` and set strong local secrets.
2. Run `docker compose up --build -d`.
3. Open the dashboard at http://localhost:3000 and API docs at http://localhost:8000/docs.

See `docs/DEPLOYMENT.md`, `docs/SECURITY.md`, and `docs/FINAL_IMPLEMENTATION_STATUS.md` for setup, security boundaries, and verification details.
