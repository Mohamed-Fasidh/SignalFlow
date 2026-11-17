# Deployment Guide

## 1. Local Docker deployment

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Generate secrets, for example `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
4. Set `SECRET_KEY` and `WEBHOOK_SIGNING_SECRET` to different random values.
5. Run `docker compose up --build`.
6. Run `docker compose exec api python -m app.scripts.seed_demo`.
7. Visit `http://localhost:3000` and `http://localhost:8000/docs`.

Local Compose initializes three database roles: an admin used only for initialization, a migration owner used only by the one-off migration service, and a restricted runtime role used by the API and worker. The API role has no `BYPASSRLS` privilege. The supplied passwords are development-only; replace them before exposing any service and use a secret manager outside local development. Never reuse them in a public environment.

## 2. AWS reference deployment

Recommended initial production topology:

- Route 53 + ACM TLS certificate
- Application Load Balancer in public subnets
- ECS Fargate API service in private subnets
- ECS Fargate worker service in private subnets
- RDS PostgreSQL Multi-AZ with encryption and automated backups
- ElastiCache Redis in private subnets
- ECR for immutable container images
- Secrets Manager for database and provider credentials
- CloudWatch Logs and alarms
- S3 for encrypted exports/object storage if needed
- WAF on the public entry point

Do not expose PostgreSQL or Redis publicly.

## 3. CI/CD release sequence

1. Pull request: Ruff, pytest, type checks, dependency/security scanning.
2. Merge to protected `main`: build versioned API and worker images.
3. Push images to ECR using GitHub OIDC (avoid long-lived AWS keys).
4. Run Alembic migration as a one-off ECS task.
5. Deploy API and worker task definitions.
6. Run smoke tests against `/health/ready` and a tenant-scoped test route.
7. Monitor error rate, latency and queue depth; rollback to the prior image if release health fails.

Use separate AWS accounts/environments for development, staging and production.

## 4. Database operations

- Enable automated backups and point-in-time recovery.
- Set retention according to legal and business requirements.
- Test restore into an isolated environment at least quarterly.
- Run migrations as a release task, not independently in every API replica.
- Use a migration lock/release gate and review destructive migrations.
- Monitor connection count, CPU, storage, slow queries and replication health.

## 5. Go-live checklist

- [ ] OIDC/JWT auth and RBAC implemented
- [ ] Tenant isolation verified with automated negative tests (`TEST_POSTGRES_URL` enables the PostgreSQL RLS integration test)
- [ ] Secrets moved to Secrets Manager
- [ ] TLS enforced; CORS restricted to production domains
- [ ] Database private; encryption at rest and in transit
- [ ] Backups and restore drill verified
- [ ] Rate limits and request body limits configured
- [ ] Webhook signature + timestamp/replay validation implemented
- [ ] CRM OAuth scopes and token rotation reviewed
- [ ] GDPR/privacy review and data source permissions approved
- [ ] Logs redact tokens and unnecessary personal data
- [ ] Alerts for API errors, queue backlog, failed jobs and database saturation
- [ ] Load and security testing completed
- [ ] Incident response and rollback runbooks reviewed

### PostgreSQL runtime-role example

For production, do not run the API as the schema/table owner. Run Alembic with a migration owner, then grant the runtime role only the required DML permissions. Adapt role names, passwords and schema ownership to your secret-management process:

```sql
CREATE ROLE signalflow_runtime LOGIN PASSWORD '<managed-secret>' NOBYPASSRLS;
GRANT CONNECT ON DATABASE signalflow TO signalflow_runtime;
GRANT USAGE ON SCHEMA public TO signalflow_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO signalflow_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO signalflow_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE signalflow_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO signalflow_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE signalflow_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO signalflow_runtime;
```

Set the API's `DATABASE_URL` to `signalflow_runtime`, not the migration owner. The role must not be granted `BYPASSRLS`, and must not be a superuser. The optional RLS test asserts these conditions and checks that a tenant cannot see another tenant's account rows.
