# Security model and production blockers

## Implemented safeguards

- All account and signal reads/writes are scoped by tenant ID in application queries.
- In `local`, `development` and `test` modes, `X-Tenant-ID` selects a demo tenant. This header is untrusted and must never be enabled on a public deployment.
- Other modes require an HS256 signed bearer JWT with `tenant_id`, `iat` and `exp` claims. The API verifies signature, expiry and UUID shape. Production requires configured `JWT_ISSUER` and `JWT_AUDIENCE`; tokens with mismatched issuer or audience are rejected. The signing key must be shared securely with the trusted identity provider, rotated, and stored in a managed secret store.
- Production startup rejects the known development secrets and requires secrets of at least 32 characters.
- Native HubSpot v3 webhook signatures use constant-time comparison and a five-minute timestamp tolerance; local HMAC envelopes are restricted to non-production modes. Oversized webhook bodies and malformed JSON are rejected.
- SQL statements are parameterized through SQLAlchemy; domains and request fields are validated.
- External AI output is schema-validated and is not allowed to trigger CRM writes automatically.

## Not yet production-certified

- No user directory, login/session issuance, password reset, MFA, SSO, role-based access control or fine-grained permissions are included. JWT issuer/audience checks are implemented, but token issuance and tenant-membership authorization must be provided by a trusted external identity provider.
- PostgreSQL RLS is configured by migration `0002_rls_webhooks` and set transaction-locally for API requests. Run the optional PostgreSQL RLS integration test against the exact runtime role; the role must not be superuser or have `BYPASSRLS`.
- The demo HubSpot token is a single-tenant private-app credential, not OAuth. Per-tenant encrypted token vaulting and OAuth lifecycle are outstanding.
- Webhook events are persisted with tenant-scoped uniqueness for replay protection. Native HubSpot delivery still requires correct app-secret and portal-to-tenant configuration; a dead-letter/reprocessing UI is not included.
- AI research does not browse or verify sources. It must not be treated as factual enrichment without a source-backed retrieval system and human review.
- No production secrets manager, TLS termination, WAF, rate limiting, penetration test, privacy review, formal data-retention workflow or incident-response process is provisioned by this repository.

Never deploy with `APP_ENV=local`, never expose the demo tenant header, and never commit `.env` or provider tokens. The local Compose stack uses a dedicated restricted runtime database role; production should preserve this role separation with managed secret rotation.


## PostgreSQL row-level security

Migration `0002_rls_webhooks` enables and forces RLS for `accounts`, `buying_signals`, `audit_events`, `webhook_events`, and `research_jobs`. The API sets `app.current_tenant` transaction-locally at the SQLAlchemy session boundary. The database role used by the API must not be a superuser and must not have `BYPASSRLS`; use a separate owner role for schema migrations and a restricted runtime role for the application. Verify this explicitly in the deployed database before loading customer data.

## Webhook replay protection

The webhook inbox has a unique `(tenant_id, provider, event_id)` key. Repeated deliveries are acknowledged as duplicates and are not inserted twice. In production, configure `HUBSPOT_CLIENT_SECRET` and `HUBSPOT_WEBHOOK_TENANT_ID`; HubSpot v3 signatures and request timestamps are verified. The local generic HMAC envelope is for development only.
