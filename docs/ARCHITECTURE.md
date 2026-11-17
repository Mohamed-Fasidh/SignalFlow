# Architecture Decision Record

## System boundaries

- API: request validation, tenant scoping, synchronous CRUD and orchestration.
- PostgreSQL: durable system of record.
- Redis/Celery: asynchronous execution and transient coordination.
- Integrations: provider-specific adapters isolated from domain services.
- AI: advisory research with validated structured output and evidence.
- Frontend: user interface; never trusted for authorization.

## Key decisions

1. **Modular monolith first.** The API and worker share domain code but run as separate processes. Split services only when scaling or team ownership justifies it.
2. **PostgreSQL first.** Avoid a separate warehouse until analytical volume and query patterns justify it.
3. **Deterministic scoring.** Explainability and reproducibility matter more than an opaque LLM score.
4. **At-least-once task execution.** Workers may retry; every external side effect must use idempotency keys and deduplication.
5. **Human-in-the-loop AI.** Research and draft generation are allowed; sending messages and modifying CRM data require approval.
6. **Tenant boundary.** Tenant IDs are included in tenant-owned rows and queries. PostgreSQL RLS policies are enforced through transaction-local tenant context; use a non-superuser runtime role without `BYPASSRLS` and run the optional PostgreSQL isolation test before production.

## Production hardening gaps

- OIDC/JWT validation and role-based permissions
- External OIDC/JWKS issuer and audience validation, user-level RBAC and tenant membership authorization
- Live PostgreSQL RLS integration test against the production runtime role
- Real HubSpot OAuth lifecycle and sync conflict policy
- Per-portal HubSpot tenant mapping, dead-letter/reprocessing workflow and webhook event processing pipeline
- Transactional outbox for reliable external event delivery
- Rate limiting, request size limits and abuse protection
- PII classification, retention, deletion and export workflows
- OpenTelemetry tracing, metrics, alerting and SLOs
- Load, chaos, security and restore testing
