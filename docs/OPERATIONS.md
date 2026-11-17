# Operations Runbook

## Health

- Liveness: `GET /health/live`
- Readiness: `GET /health/ready` (checks PostgreSQL and Redis)
- Celery worker: inspect worker logs and queue depth (`celery -A app.workers.celery_app:celery_app inspect active`).

## Common incidents

### API returns 503
1. Check RDS/PostgreSQL availability and network/security groups.
2. Check connection pool exhaustion and database CPU.
3. Verify current migration revision.
4. Restore service only after database health is confirmed.

### Queue backlog grows
1. Inspect failed/retrying tasks and provider rate limits.
2. Check Redis memory and connectivity.
3. Scale workers only after confirming downstream provider capacity.
4. Do not blindly purge queues; preserve task payloads for investigation.

### CRM sync failures
1. Inspect sanitized provider response and correlation ID.
2. Check OAuth expiry, scopes and provider rate limits.
3. Retry only idempotent operations.
4. Record manual reconciliation when provider state is ambiguous.

### Suspected credential exposure
1. Revoke/rotate the credential at its provider.
2. Update secret manager and restart affected tasks.
3. Review audit logs and access history.
4. Follow incident response and customer notification policies.

## Operational metrics to add

- API request rate, latency percentiles and 5xx rate
- Ingestion records processed / rejected / deduplicated
- Worker queue depth, task age, retry and dead-letter counts
- CRM sync success rate and provider 429s
- Data freshness by source
- Lead score distribution and human-reviewed conversion outcomes
