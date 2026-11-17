"""Validated request and response contracts for the public API."""
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class AccountCreate(BaseModel):
    """A company record supplied by an API client or ingestion source."""

    name: str = Field(min_length=1, max_length=240)
    domain: str = Field(min_length=3, max_length=255)
    industry: str | None = Field(default=None, max_length=120)
    employee_count: int | None = Field(default=None, ge=1, le=10_000_000)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    tier: str = Field(default="unknown", pattern="^(unknown|smb|mid_market|enterprise)$")
    description: str | None = Field(default=None, max_length=10_000)

    @field_validator("name", "domain", mode="before")
    @classmethod
    def strip_required_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("industry", "description", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class AccountRead(BaseModel):
    id: UUID
    name: str
    domain: str
    industry: str | None
    employee_count: int | None
    country: str | None
    score: int
    priority: str = "normal"
    is_pinned: bool = False
    tier: str = "unknown"
    crm_synced_at: datetime | None = None
    score_reasons: list[dict[str, Any]]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SignalCreate(BaseModel):
    account_id: UUID
    signal_type: str = Field(
        pattern="^(compliance_requirement|security_hiring|enterprise_expansion|funding|icp_fit|other)$"
    )
    description: str = Field(min_length=5, max_length=4000)
    source_url: HttpUrl | None = None
    source_name: str = Field(default="manual", min_length=1, max_length=120)
    confidence: int = Field(default=70, ge=0, le=100)
    occurred_at: datetime | None = None

    @field_validator("description", "source_name", mode="before")
    @classmethod
    def strip_signal_text(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return value.astimezone(timezone.utc) if value else value


class SignalRead(BaseModel):
    id: UUID
    signal_type: str
    description: str
    source_url: str | None
    source_name: str
    confidence: int
    occurred_at: datetime
    model_config = ConfigDict(from_attributes=True)


class IngestAccounts(BaseModel):
    records: list[AccountCreate] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def reject_duplicate_domains(self) -> "IngestAccounts":
        domains = [record.domain.casefold() for record in self.records]
        if len(domains) != len(set(domains)):
            raise ValueError("records must not contain duplicate company domains")
        return self


class IngestResult(BaseModel):
    created: int = Field(ge=0)
    updated: int = Field(ge=0)
    account_ids: list[UUID]
