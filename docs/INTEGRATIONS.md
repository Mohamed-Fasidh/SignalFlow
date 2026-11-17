# Integrations and activation guide

## HubSpot company sync

The API includes `POST /api/v1/accounts/{account_id}/hubspot-sync` and an async HubSpot CRM v3 company adapter. For a local single-tenant proof of concept, create a HubSpot private app with only the required CRM company read/write scopes and set both `HUBSPOT_PRIVATE_APP_TOKEN` and `HUBSPOT_DEMO_TENANT_ID` in `.env`. The tenant allowlist is mandatory and prevents the shared demo token from being used by other tenant IDs.

This is **not multi-tenant OAuth**. Do not use one private-app token for multiple customer tenants. A commercial multi-tenant deployment must implement the HubSpot OAuth authorization-code flow, tenant-bound encrypted refresh/access-token storage, token refresh, installation/uninstallation handling, per-tenant scopes and audit records. The demo token setting is deliberately a single-tenant integration switch.

## AI account research

The API includes `POST /api/v1/accounts/{account_id}/research`. It calls an OpenAI-compatible chat-completions endpoint and validates the response against a strict Pydantic schema. Configure `AI_API_KEY`, `AI_BASE_URL` and `AI_MODEL`.

The current provider analyzes only the account fields already stored in SignalFlow. It does not crawl the web, validate external claims or independently discover evidence. The returned confidence and URLs are model output, not verified facts. Do not use the output for autonomous outreach, credit decisions or other consequential actions. A production research pipeline needs approved source connectors, source capture, provenance, prompt-injection isolation, retention rules and human review.

## Webhook signatures and event inbox

In local/development/test modes, `POST /api/v1/webhooks/hubspot` accepts a JSON object containing `tenant_id`, `event_id` and `event_type`. The sender must HMAC-SHA256 sign the **exact raw request bytes** using `WEBHOOK_SIGNING_SECRET` and send the lowercase hex digest in `X-Webhook-Signature` (optionally prefixed with `sha256=`). This local contract is not the format used by HubSpot.

In production, configure `HUBSPOT_CLIENT_SECRET` and `HUBSPOT_WEBHOOK_TENANT_ID`. The endpoint verifies HubSpot v3's signature and timestamp headers and accepts HubSpot's event-array payload. Each event is persisted with a tenant/provider/event uniqueness key; duplicate deliveries are acknowledged without a second insert. Configure a portal-to-tenant mapping per customer before supporting multiple portals; the current environment setting supports one portal mapping.

AI provider configuration is also shared at the application level in this starter. Before sending any tenant's account data to an external model provider, establish the applicable data-processing terms, tenant disclosure/consent and retention settings. A multi-tenant SaaS release should add per-tenant provider configuration or a documented platform-level subprocessor policy.


## HubSpot webhook setup

For production, set `HUBSPOT_CLIENT_SECRET` to the HubSpot app's client secret and `HUBSPOT_WEBHOOK_TENANT_ID` to the tenant UUID that owns this portal connection. The endpoint validates `X-HubSpot-Signature-v3` and `X-HubSpot-Request-Timestamp` using HubSpot's v3 canonical request format and a five-minute tolerance. Each webhook event is persisted in the idempotent inbox. Map each HubSpot portal to its own tenant before enabling multiple portals; the single tenant setting is intentionally a one-portal deployment configuration.

The existing private-app company upsert is a single-tenant integration. It is not an OAuth installation flow and should not be represented as a multi-customer HubSpot marketplace app. For multi-customer SaaS, implement OAuth authorization-code flow, encrypted per-tenant refresh tokens, token rotation, portal-to-tenant mapping, uninstall handling and scope minimization before onboarding external tenants.
