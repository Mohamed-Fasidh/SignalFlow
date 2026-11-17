import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, Index, Uuid, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

UUID_TYPE = Uuid(as_uuid=True)
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "domain", name="uq_account_tenant_domain"),
        UniqueConstraint("id", "tenant_id", name="uq_account_id_tenant"),
        Index("ix_accounts_tenant_score", "tenant_id", "score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    country: Mapped[str | None] = mapped_column(String(2))
    description: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="normal", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(default=False, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    crm_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score_reasons: Mapped[list] = mapped_column(JSON_TYPE, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    signals: Mapped[list["BuyingSignal"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class BuyingSignal(Base):
    __tablename__ = "buying_signals"
    __table_args__ = (
        ForeignKeyConstraint(["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], ondelete="CASCADE", name="fk_signal_account_tenant"),
        Index("ix_signals_account_type", "account_id", "signal_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, index=True, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    signal_type: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    source_name: Mapped[str] = mapped_column(String(120), default="manual")
    confidence: Mapped[int] = mapped_column(Integer, default=70)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    account: Mapped[Account] = relationship(back_populates="signals")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict] = mapped_column(JSON_TYPE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", "event_id", name="uq_webhook_tenant_provider_event"),
        Index("ix_webhook_tenant_received", "tenant_id", "received_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="hubspot")
    event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ResearchJob(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (
        ForeignKeyConstraint(["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"],
                             ondelete="CASCADE", name="fk_research_account_tenant"),
        Index("ix_research_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID_TYPE, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON_TYPE)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
