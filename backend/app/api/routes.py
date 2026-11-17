from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.core.tenant import get_tenant_db, tenant_dependency
from app.models.entities import Account, BuyingSignal, AuditEvent, WebhookEvent, ResearchJob
from app.api.schemas import AccountCreate, AccountRead, SignalCreate, SignalRead, IngestAccounts, IngestResult
from app.services.normalization import normalize_domain
from app.services.scoring import score_signals

router = APIRouter()


@router.post("/accounts", response_model=AccountRead, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    try:
        domain = normalize_domain(payload.domain)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    existing = db.scalar(select(Account).where(Account.tenant_id == tenant_id, Account.domain == domain))
    if existing:
        raise HTTPException(status_code=409, detail="Account domain already exists for this tenant")
    account = Account(tenant_id=tenant_id, domain=domain, **payload.model_dump(exclude={"domain"}))
    db.add(account)
    db.flush()
    db.add(AuditEvent(tenant_id=tenant_id, action="account.created", resource_type="account",
                      resource_id=str(account.id), details={"domain": domain}))
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    crm_synced: bool | None = Query(default=None),
    tier: str | None = Query(default=None, pattern="^(unknown|smb|mid_market|enterprise)$"),
    db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)
):
    stmt = select(Account).where(Account.tenant_id == tenant_id).order_by(Account.is_pinned.desc(), Account.score.desc()).limit(limit).offset(offset)
    if crm_synced is True:
        stmt = stmt.where(Account.crm_synced_at.is_not(None))
    if crm_synced is False:
        stmt = stmt.where(Account.crm_synced_at.is_(None))
    if tier:
        stmt = stmt.where(Account.tier == tier)
    if q:
        term = q.strip()
        if term:
            stmt = stmt.where(
                or_(
                    func.lower(Account.name).contains(term.casefold(), autoescape=True),
                    func.lower(Account.domain).contains(term.casefold(), autoescape=True),
                    func.lower(Account.industry).contains(term.casefold(), autoescape=True),
                )
            )
    return list(db.scalars(stmt).all())


@router.get("/accounts/{account_id}", response_model=AccountRead)
def get_account(account_id: UUID, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    account = db.scalar(select(Account).options(selectinload(Account.signals)).where(
        Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/signals", response_model=SignalRead, status_code=201)
def create_signal(payload: SignalCreate, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    account = db.scalar(select(Account).where(Account.id == payload.account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    signal = BuyingSignal(
        tenant_id=tenant_id, account_id=account.id, signal_type=payload.signal_type,
        description=payload.description, source_url=str(payload.source_url) if payload.source_url else None,
        source_name=payload.source_name, confidence=payload.confidence,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc), account=account
    )
    db.add(signal)
    db.flush()
    account.score, account.score_reasons = score_signals(account.signals)
    db.add(AuditEvent(tenant_id=tenant_id, action="signal.created", resource_type="signal",
                      resource_id=str(signal.id), details={"type": signal.signal_type, "updated_score": account.score}))
    db.commit()
    db.refresh(signal)
    return signal


@router.post("/accounts/{account_id}/score", response_model=AccountRead)
def recalculate_score(account_id: UUID, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    account = db.scalar(select(Account).options(selectinload(Account.signals)).where(
        Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.score, account.score_reasons = score_signals(account.signals)
    db.add(AuditEvent(tenant_id=tenant_id, action="account.scored", resource_type="account",
                      resource_id=str(account.id), details={"score": account.score}))
    db.commit()
    db.refresh(account)
    return account


@router.get("/leads/prioritized", response_model=list[AccountRead])
def prioritized_leads(limit: int = Query(default=25, ge=1, le=100), offset: int = Query(default=0, ge=0),
                      crm_synced: bool | None = Query(default=None),
                      tier: str | None = Query(default=None, pattern="^(unknown|smb|mid_market|enterprise)$"),
                      db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    stmt = select(Account).where(Account.tenant_id == tenant_id)
    if crm_synced is True:
        stmt = stmt.where(Account.crm_synced_at.is_not(None))
    elif crm_synced is False:
        stmt = stmt.where(Account.crm_synced_at.is_(None))
    if tier:
        stmt = stmt.where(Account.tier == tier)
    stmt = stmt.order_by(Account.is_pinned.desc(), Account.score.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.post("/ingestion/accounts", response_model=IngestResult)
def ingest_accounts(payload: IngestAccounts, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    # Validate and canonicalize the entire batch before mutating the session. This
    # prevents URL variants (for example, www.example.com and example.com) from
    # silently overwriting one another within a single request.
    normalized_records: list[tuple[AccountCreate, str]] = []
    seen_domains: set[str] = set()
    for item in payload.records:
        try:
            domain = normalize_domain(item.domain)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{item.domain}: {exc}") from exc
        if domain in seen_domains:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate company domain after normalization: {domain}",
            )
        seen_domains.add(domain)
        normalized_records.append((item, domain))

    created = updated = 0
    ids = []
    for item, domain in normalized_records:
        account = db.scalar(select(Account).where(Account.tenant_id == tenant_id, Account.domain == domain))
        if account:
            for key, value in item.model_dump(exclude={"domain"}).items():
                setattr(account, key, value)
            updated += 1
        else:
            account = Account(tenant_id=tenant_id, domain=domain, **item.model_dump(exclude={"domain"}))
            db.add(account)
            db.flush()
            created += 1
        ids.append(account.id)
    db.add(AuditEvent(tenant_id=tenant_id, action="accounts.ingested", resource_type="batch",
                      resource_id="bulk", details={"created": created, "updated": updated}))
    db.commit()
    return IngestResult(created=created, updated=updated, account_ids=ids)


@router.get("/accounts/{account_id}/signals", response_model=list[SignalRead])
def list_account_signals(account_id: UUID, limit: int = Query(default=100, ge=1, le=500),
                         include_archived: bool = Query(default=False), db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    account = db.scalar(select(Account.id).where(Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    stmt = select(BuyingSignal).where(BuyingSignal.account_id == account_id,
                                     BuyingSignal.tenant_id == tenant_id)
    if not include_archived:
        stmt = stmt.where(BuyingSignal.archived_at.is_(None))
    stmt = stmt.order_by(BuyingSignal.occurred_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.post("/accounts/{account_id}/research", status_code=202)
def research_account(account_id: UUID, db: Session = Depends(get_tenant_db),
                     tenant_id: UUID = Depends(tenant_dependency)):
    account = db.scalar(select(Account).where(Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    job = ResearchJob(tenant_id=tenant_id, account_id=account.id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        from app.workers.tasks import generate_account_research
        task = generate_account_research.apply_async(args=[str(job.id), str(account.id), str(tenant_id)])
        job.task_id = task.id
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error = "Could not enqueue the AI research task. Check the Celery broker and worker."
        db.commit()
        raise HTTPException(status_code=503, detail=job.error) from exc
    return {"research_job_id": str(job.id), "task_id": job.task_id, "status": job.status}


@router.get("/research/jobs/{job_id}")
def get_research_job(job_id: UUID, db: Session = Depends(get_tenant_db),
                     tenant_id: UUID = Depends(tenant_dependency)):
    job = db.scalar(select(ResearchJob).where(ResearchJob.id == job_id, ResearchJob.tenant_id == tenant_id))
    if not job:
        raise HTTPException(status_code=404, detail="Research job not found")
    return {"id": str(job.id), "account_id": str(job.account_id), "task_id": job.task_id,
            "status": job.status, "result": job.result, "error": job.error,
            "created_at": job.created_at.isoformat(), "updated_at": job.updated_at.isoformat()}


@router.post("/accounts/{account_id}/hubspot-sync")
async def sync_account_to_hubspot(account_id: UUID, db: Session = Depends(get_tenant_db),
                                  tenant_id: UUID = Depends(tenant_dependency)):
    from app.core.config import settings
    from app.integrations.hubspot import HubSpotClient
    account = db.scalar(select(Account).where(Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not settings.hubspot_private_app_token or not settings.hubspot_demo_tenant_id:
        raise HTTPException(status_code=503, detail="HubSpot is not configured. Set the token and explicit demo tenant allowlist.")
    if str(tenant_id) != settings.hubspot_demo_tenant_id:
        raise HTTPException(status_code=403, detail="HubSpot demo connection is not enabled for this tenant")
    try:
        result = await HubSpotClient(settings.hubspot_private_app_token).upsert_company({
            "name": account.name, "domain": account.domain, "industry": account.industry,
            "employee_count": account.employee_count, "country": account.country,
            "description": account.description,
        })
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="HubSpot API request failed") from exc
    account.crm_synced_at = datetime.now(timezone.utc)
    db.add(AuditEvent(tenant_id=tenant_id, action="account.hubspot_synced", resource_type="account",
                      resource_id=str(account.id), details={"hubspot_id": result.get("id")}))
    db.commit()
    return {"status": "synced", "hubspot_id": result.get("id")}


@router.post("/webhooks/hubspot", status_code=202)
async def receive_hubspot_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive native HubSpot v3 webhooks or a local HMAC-signed test envelope."""
    import hashlib
    import json
    from app.core.config import settings
    from app.integrations.webhook_security import verify_hmac_sha256, verify_hubspot_v3

    raw_body = await request.body()
    if len(raw_body) > settings.max_request_body_bytes:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    native_hubspot = bool(settings.hubspot_client_secret)
    if native_hubspot:
        verify_hubspot_v3(
            request, raw_body, settings.hubspot_client_secret,
            request.headers.get("X-HubSpot-Signature-v3"),
            request.headers.get("X-HubSpot-Request-Timestamp"),
        )
    elif settings.app_env.lower() == "production":
        raise HTTPException(status_code=503, detail="Configure HUBSPOT_CLIENT_SECRET for native HubSpot webhook verification")
    else:
        verify_hmac_sha256(raw_body, request.headers.get("X-Webhook-Signature"),
                           settings.webhook_signing_secret)

    try:
        body = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from exc

    if native_hubspot:
        if not settings.hubspot_webhook_tenant_id:
            raise HTTPException(status_code=503, detail="HUBSPOT_WEBHOOK_TENANT_ID is not configured")
        tenant_value = settings.hubspot_webhook_tenant_id
        events = body if isinstance(body, list) else [body]
    else:
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Local webhook envelope must be a JSON object")
        tenant_value = body.get("tenant_id")
        events = [body]

    try:
        tenant_id = UUID(str(tenant_value))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Webhook tenant_id is required") from exc
    db.info["tenant_id"] = tenant_id

    accepted, duplicates = [], []
    for item in events:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each webhook event must be an object")
        raw_event_id = item.get("event_id") or item.get("eventId")
        event_id = str(raw_event_id or hashlib.sha256(
            json.dumps(item, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest())[:160]
        event_type = str(item.get("event_type") or item.get("subscriptionType") or "unknown")[:120]
        try:
            with db.begin_nested():
                db.add(WebhookEvent(tenant_id=tenant_id, provider="hubspot", event_id=event_id,
                                    event_type=event_type, payload=item))
                db.flush()
        except Exception as exc:
            from sqlalchemy.exc import IntegrityError
            if not isinstance(exc, IntegrityError):
                db.rollback()
                raise
            existing = db.scalar(select(WebhookEvent).where(
                WebhookEvent.tenant_id == tenant_id, WebhookEvent.provider == "hubspot",
                WebhookEvent.event_id == event_id))
            if existing:
                duplicates.append(event_id)
                continue
            raise HTTPException(status_code=409, detail="Webhook event could not be stored") from exc
        db.add(AuditEvent(tenant_id=tenant_id, actor="hubspot-webhook", action="webhook.received",
                          resource_type="webhook", resource_id=event_id,
                          details={"event_type": event_type}))
        accepted.append(event_id)
    db.commit()
    return {"accepted": True, "accepted_count": len(accepted), "duplicate_count": len(duplicates),
            "event_ids": accepted, "duplicate_event_ids": duplicates}


@router.patch("/signals/{signal_id}/archive")
def archive_signal(signal_id: UUID, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    signal = db.scalar(select(BuyingSignal).where(BuyingSignal.id == signal_id, BuyingSignal.tenant_id == tenant_id))
    if not signal:
        raise HTTPException(status_code=404, detail="Buying signal not found")
    account = db.scalar(select(Account).options(selectinload(Account.signals)).where(
        Account.id == signal.account_id, Account.tenant_id == tenant_id))
    signal.archived_at = datetime.now(timezone.utc)
    db.flush()
    account.score, account.score_reasons = score_signals([s for s in account.signals if s.archived_at is None])
    db.add(AuditEvent(tenant_id=tenant_id, action="signal.archived", resource_type="signal",
                      resource_id=str(signal.id), details={"account_id": str(account.id)}))
    db.commit()
    return {"status": "archived", "signal_id": str(signal.id), "account_score": account.score}


@router.patch("/accounts/{account_id}/priority")
def update_account_priority(account_id: UUID, payload: dict, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    priority = payload.get("priority")
    if priority not in {"low", "normal", "high", "critical"}:
        raise HTTPException(status_code=422, detail="priority must be low, normal, high, or critical")
    account = db.scalar(select(Account).where(Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.priority = priority
    db.add(AuditEvent(tenant_id=tenant_id, action="account.priority_changed", resource_type="account",
                      resource_id=str(account.id), details={"priority": priority}))
    db.commit()
    return {"status": "updated", "priority": priority}


@router.get("/audit/events")
def list_audit_events(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                      db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    rows = db.scalars(select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
                      .order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)).all()
    return [{"id": str(row.id), "actor": row.actor, "action": row.action,
             "resource_type": row.resource_type, "resource_id": row.resource_id,
             "details": row.details, "created_at": row.created_at.isoformat()} for row in rows]


@router.get("/webhooks/events")
def list_webhook_events(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                        db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    rows = db.scalars(select(WebhookEvent).where(WebhookEvent.tenant_id == tenant_id)
                      .order_by(WebhookEvent.received_at.desc()).limit(limit).offset(offset)).all()
    return [{"id": str(row.id), "provider": row.provider, "event_id": row.event_id,
             "event_type": row.event_type, "payload": row.payload,
             "received_at": row.received_at.isoformat()} for row in rows]


@router.get("/integrations/hubspot/status")
def hubspot_status(db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    from app.core.config import settings
    latest = db.scalar(select(WebhookEvent).where(WebhookEvent.tenant_id == tenant_id,
                         WebhookEvent.provider == "hubspot").order_by(WebhookEvent.received_at.desc()).limit(1))
    configured = bool(settings.hubspot_private_app_token and settings.hubspot_demo_tenant_id == str(tenant_id))
    return {"configured": configured, "webhook_secret_configured": bool(settings.hubspot_client_secret),
            "last_webhook_at": latest.received_at.isoformat() if latest else None,
            "last_event_id": latest.event_id if latest else None}


@router.get("/duplicates")
def duplicate_candidates(db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    from difflib import SequenceMatcher
    rows = db.scalars(select(Account).where(Account.tenant_id == tenant_id).order_by(Account.name).limit(1000)).all()
    candidates = []
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            name_similarity = SequenceMatcher(None, left.name.casefold(), right.name.casefold()).ratio()
            domain_root = left.domain.split(".")[0].casefold() == right.domain.split(".")[0].casefold()
            if name_similarity >= 0.88 or domain_root:
                candidates.append({"source": {"id": str(left.id), "name": left.name, "domain": left.domain},
                                  "target": {"id": str(right.id), "name": right.name, "domain": right.domain},
                                  "similarity": round(name_similarity, 3)})
    return candidates[:200]


@router.post("/accounts/{source_id}/merge/{target_id}")
def merge_accounts(source_id: UUID, target_id: UUID, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    if source_id == target_id:
        raise HTTPException(status_code=422, detail="Source and target must be different accounts")
    source = db.scalar(select(Account).options(selectinload(Account.signals)).where(Account.id == source_id, Account.tenant_id == tenant_id))
    target = db.scalar(select(Account).options(selectinload(Account.signals)).where(Account.id == target_id, Account.tenant_id == tenant_id))
    if not source or not target:
        raise HTTPException(status_code=404, detail="Both accounts must exist in this tenant")
    for signal in list(source.signals):
        source.signals.remove(signal)
        target.signals.append(signal)
        signal.account_id = target.id
        signal.tenant_id = tenant_id
    db.flush()
    target.score, target.score_reasons = score_signals(target.signals)
    db.add(AuditEvent(tenant_id=tenant_id, action="account.merged", resource_type="account",
                      resource_id=str(target.id), details={"merged_account_id": str(source.id), "merged_domain": source.domain}))
    db.delete(source)
    db.commit()
    return {"status": "merged", "source_id": str(source_id), "target_id": str(target_id)}


@router.post("/accounts/{account_id}/hubspot-note")
async def push_account_note(account_id: UUID, payload: dict, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    from app.core.config import settings
    from app.integrations.hubspot import HubSpotClient
    account = db.scalar(select(Account).where(Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not settings.hubspot_private_app_token or settings.hubspot_demo_tenant_id != str(tenant_id):
        raise HTTPException(status_code=503, detail="HubSpot note sync is not configured for this tenant")
    body = str(payload.get("body", "")).strip()
    if not body or len(body) > 10000:
        raise HTTPException(status_code=422, detail="Note body must contain 1–10000 characters")
    try:
        result = await HubSpotClient(settings.hubspot_private_app_token).create_company_note(account.domain, body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="HubSpot note API request failed") from exc
    db.add(AuditEvent(tenant_id=tenant_id, action="account.hubspot_note_pushed", resource_type="account",
                      resource_id=str(account.id), details={"note_id": result.get("id")}))
    db.commit()
    return {"status": "pushed", "note_id": result.get("id")}


@router.patch("/signals/{signal_id}/restore")
def restore_signal(signal_id: UUID, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    signal = db.scalar(select(BuyingSignal).where(BuyingSignal.id == signal_id, BuyingSignal.tenant_id == tenant_id))
    if not signal:
        raise HTTPException(status_code=404, detail="Buying signal not found")
    if signal.archived_at is None:
        return {"status": "active", "signal_id": str(signal.id)}
    signal.archived_at = None
    account = db.scalar(select(Account).options(selectinload(Account.signals)).where(
        Account.id == signal.account_id, Account.tenant_id == tenant_id))
    account.score, account.score_reasons = score_signals(account.signals)
    db.add(AuditEvent(tenant_id=tenant_id, action="signal.restored", resource_type="signal",
                      resource_id=str(signal.id), details={"account_id": str(account.id)}))
    db.commit()
    return {"status": "restored", "signal_id": str(signal.id), "account_score": account.score}


@router.patch("/accounts/{account_id}/pin")
def toggle_account_pin(account_id: UUID, payload: dict, db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    pinned = payload.get("pinned")
    if not isinstance(pinned, bool):
        raise HTTPException(status_code=422, detail="pinned must be a boolean")
    account = db.scalar(select(Account).where(Account.id == account_id, Account.tenant_id == tenant_id))
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.is_pinned = pinned
    db.add(AuditEvent(tenant_id=tenant_id, action="account.pin_changed", resource_type="account",
                      resource_id=str(account.id), details={"pinned": pinned}))
    db.commit()
    return {"status": "updated", "pinned": pinned}


@router.get("/research/jobs")
def list_research_jobs(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                      db: Session = Depends(get_tenant_db), tenant_id: UUID = Depends(tenant_dependency)):
    jobs = db.scalars(select(ResearchJob).where(ResearchJob.tenant_id == tenant_id)
                      .order_by(ResearchJob.created_at.desc()).limit(limit).offset(offset)).all()
    return [{"id": str(job.id), "account_id": str(job.account_id), "task_id": job.task_id,
             "status": job.status, "result": job.result, "error": job.error,
             "created_at": job.created_at.isoformat()} for job in jobs]
