from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from app.core.database import SessionLocal
from app.models.entities import Account, AuditEvent, WebhookEvent
from app.services.scoring import score_signals
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True,
                 retry_jitter=True, max_retries=5)
def heartbeat(self) -> dict:
    return {"status": "ok", "task_id": self.request.id}


@celery_app.task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True,
                 retry_jitter=True, max_retries=5)
def recalculate_account_score(self, account_id: str, tenant_id: str) -> dict:
    """Recalculate one account in a tenant-scoped worker transaction."""
    account_uuid, tenant_uuid = UUID(account_id), UUID(tenant_id)
    with SessionLocal() as db:
        db.info["tenant_id"] = tenant_uuid
        account = db.scalar(select(Account).options(selectinload(Account.signals)).where(
            Account.id == account_uuid, Account.tenant_id == tenant_uuid))
        if account is None:
            return {"status": "not_found", "account_id": account_id}
        account.score, account.score_reasons = score_signals(account.signals)
        db.commit()
        return {"status": "updated", "account_id": account_id, "score": account.score}


@celery_app.task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True,
                 retry_jitter=True, max_retries=5)
def prune_webhook_inbox(self, tenant_id: str, retention_days: int = 30) -> dict:
    """Delete old webhook payloads for one tenant according to configured retention."""
    tenant_uuid = UUID(tenant_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(retention_days, 365)))
    with SessionLocal() as db:
        db.info["tenant_id"] = tenant_uuid
        result = db.execute(delete(WebhookEvent).where(
            WebhookEvent.tenant_id == tenant_uuid, WebhookEvent.received_at < cutoff))
        deleted = result.rowcount or 0
        db.commit()
        return {"status": "pruned", "tenant_id": tenant_id, "deleted": deleted}


@celery_app.task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True,
                 retry_jitter=True, max_retries=3)
def generate_account_research(self, research_job_id: str, account_id: str, tenant_id: str) -> dict:
    """Run structured AI research asynchronously and persist tenant-scoped output."""
    import asyncio
    from app.integrations.ai_research import ResearchProvider
    from app.models.entities import ResearchJob

    job_uuid, account_uuid, tenant_uuid = UUID(research_job_id), UUID(account_id), UUID(tenant_id)
    with SessionLocal() as db:
        db.info["tenant_id"] = tenant_uuid
        job = db.scalar(select(ResearchJob).where(ResearchJob.id == job_uuid,
                                                  ResearchJob.tenant_id == tenant_uuid))
        account = db.scalar(select(Account).where(Account.id == account_uuid,
                                                   Account.tenant_id == tenant_uuid))
        if not job or not account:
            return {"status": "not_found"}
        job.status = "running"
        db.commit()
        try:
            brief = asyncio.run(ResearchProvider().research_account({
                "name": account.name, "domain": account.domain, "industry": account.industry,
                "employee_count": account.employee_count, "country": account.country,
                "description": account.description,
            }))
            result = brief.model_dump()
            job.status = "completed"
            job.result = result
            job.error = None
            db.add(AuditEvent(tenant_id=tenant_uuid, action="account.researched",
                              resource_type="account", resource_id=str(account.id),
                              details={"research_job_id": str(job.id), "confidence": brief.confidence}))
            db.commit()
            return {"status": "completed", "research_job_id": research_job_id}
        except Exception as exc:
            db.rollback()
            failed = db.scalar(select(ResearchJob).where(ResearchJob.id == job_uuid,
                                                          ResearchJob.tenant_id == tenant_uuid))
            if failed:
                failed.status = "failed"
                failed.error = str(exc)[:1000]
                db.commit()
            raise
