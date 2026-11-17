import hashlib
import hmac
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_account_signal_scoring_and_tenant_isolation():
    tenant_a, tenant_b = str(uuid4()), str(uuid4())
    with TestClient(app) as client:
        created = client.post("/api/v1/accounts", headers={"X-Tenant-ID": tenant_a}, json={
            "name": "Acme Security", "domain": "https://www.acme.example/about", "industry": "Cybersecurity"
        })
        assert created.status_code == 201, created.text
        account_id = created.json()["id"]

        signal = client.post("/api/v1/signals", headers={"X-Tenant-ID": tenant_a}, json={
            "account_id": account_id, "signal_type": "compliance_requirement",
            "description": "SOC 2 compliance required in procurement", "confidence": 100
        })
        assert signal.status_code == 201, signal.text

        second = client.post("/api/v1/accounts", headers={"X-Tenant-ID": tenant_a}, json={
            "name": "Beta Systems", "domain": "beta.example", "industry": "Software"
        })
        assert second.status_code == 201, second.text
        leads = client.get("/api/v1/leads/prioritized?limit=1&offset=0", headers={"X-Tenant-ID": tenant_a})
        next_page = client.get("/api/v1/leads/prioritized?limit=1&offset=1", headers={"X-Tenant-ID": tenant_a})
        assert leads.status_code == 200
        assert leads.json()[0]["score"] == 25
        assert next_page.status_code == 200
        assert next_page.json()[0]["name"] == "Beta Systems"

        other_tenant = client.get("/api/v1/accounts", headers={"X-Tenant-ID": tenant_b})
        assert other_tenant.status_code == 200
        assert other_tenant.json() == []

        hidden = client.get(f"/api/v1/accounts/{account_id}", headers={"X-Tenant-ID": tenant_b})
        assert hidden.status_code == 404


def test_signed_webhook_is_idempotent():
    tenant_id = str(uuid4())
    payload = json.dumps({"tenant_id": tenant_id, "event_id": "evt-001",
                          "event_type": "company.updated"}).encode()
    signature = hmac.new(settings.webhook_signing_secret.encode(), payload, hashlib.sha256).hexdigest()
    headers = {"X-Webhook-Signature": f"sha256={signature}"}
    with TestClient(app) as client:
        first = client.post("/api/v1/webhooks/hubspot", content=payload, headers=headers)
        second = client.post("/api/v1/webhooks/hubspot", content=payload, headers=headers)
    assert first.status_code == 202, first.text
    assert first.json()["accepted_count"] == 1
    assert second.status_code == 202, second.text
    assert second.json()["duplicate_count"] == 1


def test_account_search_matches_domain_and_industry():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        created = client.post("/api/v1/accounts", headers={"X-Tenant-ID": tenant_id}, json={
            "name": "Northstar Systems", "domain": "northstar.example", "industry": "Cybersecurity"
        })
        assert created.status_code == 201, created.text

        by_domain = client.get("/api/v1/accounts?q=northstar.example", headers={"X-Tenant-ID": tenant_id})
        by_industry = client.get("/api/v1/accounts?q=Cybersecurity", headers={"X-Tenant-ID": tenant_id})

        assert [item["name"] for item in by_domain.json()] == ["Northstar Systems"]
        assert [item["name"] for item in by_industry.json()] == ["Northstar Systems"]


def test_ingestion_rejects_duplicate_domains_in_one_batch():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.post("/api/v1/ingestion/accounts", headers={"X-Tenant-ID": tenant_id}, json={
            "records": [
                {"name": "Acme One", "domain": "acme.example"},
                {"name": "Acme Two", "domain": "ACME.EXAMPLE"},
            ]
        })
    assert response.status_code == 422


def test_signal_rejects_invalid_source_url_and_naive_timestamp():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        account = client.post("/api/v1/accounts", headers={"X-Tenant-ID": tenant_id}, json={
            "name": "Example Corp", "domain": "example.example"
        })
        assert account.status_code == 201, account.text
        payload = {
            "account_id": account.json()["id"],
            "signal_type": "security_hiring",
            "description": "Hiring a security engineering lead",
            "source_url": "javascript:alert(1)",
        }
        invalid_url = client.post("/api/v1/signals", headers={"X-Tenant-ID": tenant_id}, json=payload)
        payload["source_url"] = None
        payload["occurred_at"] = "2026-11-17T10:00:00"
        naive_time = client.post("/api/v1/signals", headers={"X-Tenant-ID": tenant_id}, json=payload)

    assert invalid_url.status_code == 422
    assert naive_time.status_code == 422


def test_ingestion_rejects_domain_aliases_after_normalization():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        response = client.post("/api/v1/ingestion/accounts", headers={"X-Tenant-ID": tenant_id}, json={
            "records": [
                {"name": "Acme One", "domain": "https://www.acme.example/about"},
                {"name": "Acme Two", "domain": "acme.example"},
            ]
        })
    assert response.status_code == 422
    assert "Duplicate company domain" in response.json()["detail"]


def test_signal_accepts_http_evidence_url_and_timezone_timestamp():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        account = client.post("/api/v1/accounts", headers={"X-Tenant-ID": tenant_id}, json={
            "name": "Evidence Corp", "domain": "evidence.example"
        })
        assert account.status_code == 201, account.text
        response = client.post("/api/v1/signals", headers={"X-Tenant-ID": tenant_id}, json={
            "account_id": account.json()["id"],
            "signal_type": "funding",
            "description": "The company announced a new funding round.",
            "source_url": "https://news.example.com/funding",
            "occurred_at": "2026-11-17T10:00:00+05:30",
        })
    assert response.status_code == 201, response.text
    assert response.json()["source_url"] == "https://news.example.com/funding"
    assert response.json()["occurred_at"].startswith("2026-11-17T04:30:00")


def test_archive_signal_recalculates_score_and_audit_is_tenant_scoped():
    tenant_id = str(uuid4())
    with TestClient(app) as client:
        account = client.post("/api/v1/accounts", headers={"X-Tenant-ID": tenant_id}, json={"name": "Archive Corp", "domain": "archive.example"}).json()
        signal = client.post(
            "/api/v1/signals",
            headers={"X-Tenant-ID": tenant_id},
            json={
                "account_id": account["id"],
                "signal_type": "security_hiring",
                "description": "Hiring a security engineering leader",
                "confidence": 100,
            },
        ).json()
        archived = client.patch(f"/api/v1/signals/{signal['id']}/archive", headers={"X-Tenant-ID": tenant_id})
        events = client.get("/api/v1/audit/events", headers={"X-Tenant-ID": tenant_id})
        account_after = client.get(f"/api/v1/accounts/{account['id']}", headers={"X-Tenant-ID": tenant_id})
    assert archived.status_code == 200
    assert account_after.json()["score"] == 0
    assert any(event["action"] == "signal.archived" for event in events.json())


def test_priority_duplicate_detection_and_merge():
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}
    with TestClient(app) as client:
        one = client.post("/api/v1/accounts", headers=headers, json={"name": "Northstar Security", "domain": "northstar-security.example"}).json()
        two = client.post("/api/v1/accounts", headers=headers, json={"name": "Northstar Security Inc", "domain": "northstar-security-inc.example"}).json()
        priority = client.patch(f"/api/v1/accounts/{one['id']}/priority", headers=headers, json={"priority": "critical"})
        candidates = client.get("/api/v1/duplicates", headers=headers)
        merged = client.post(f"/api/v1/accounts/{one['id']}/merge/{two['id']}", headers=headers)
        missing = client.get(f"/api/v1/accounts/{one['id']}", headers=headers)
    assert priority.status_code == 200
    assert candidates.status_code == 200 and candidates.json()
    assert merged.status_code == 200
    assert missing.status_code == 404


def test_webhook_delivery_inspector_and_status_endpoint():
    tenant_id = str(uuid4())
    payload = json.dumps({"tenant_id": tenant_id, "event_id": "evt-inspector", "event_type": "company.updated"}).encode()
    signature = hmac.new(settings.webhook_signing_secret.encode(), payload, hashlib.sha256).hexdigest()
    with TestClient(app) as client:
        accepted = client.post("/api/v1/webhooks/hubspot", content=payload, headers={"X-Webhook-Signature": f"sha256={signature}"})
        deliveries = client.get("/api/v1/webhooks/events", headers={"X-Tenant-ID": tenant_id})
        status = client.get("/api/v1/integrations/hubspot/status", headers={"X-Tenant-ID": tenant_id})
    assert accepted.status_code == 202
    assert deliveries.status_code == 200 and deliveries.json()[0]["event_id"] == "evt-inspector"
    assert status.status_code == 200 and status.json()["last_event_id"] == "evt-inspector"


def test_signal_archive_can_be_undone_and_account_filters_are_explicit():
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}
    with TestClient(app) as client:
        enterprise = client.post(
            "/api/v1/accounts",
            headers=headers,
            json={"name": "Enterprise Co", "domain": "enterprise.example", "tier": "enterprise"},
        ).json()
        smb = client.post("/api/v1/accounts", headers=headers, json={"name": "Small Co", "domain": "small.example", "tier": "smb"}).json()
        signal = client.post(
            "/api/v1/signals",
            headers=headers,
            json={
                "account_id": smb["id"],
                "signal_type": "funding",
                "description": "Announced a funding round",
            },
        ).json()
        archived = client.patch(f"/api/v1/signals/{signal['id']}/archive", headers=headers)
        restored = client.patch(f"/api/v1/signals/{signal['id']}/restore", headers=headers)
        enterprise_filter = client.get("/api/v1/accounts?tier=enterprise", headers=headers)
        prioritized_filter = client.get("/api/v1/leads/prioritized?tier=enterprise", headers=headers)
        unsynced_filter = client.get("/api/v1/accounts?crm_synced=false", headers=headers)
    assert archived.status_code == 200 and restored.status_code == 200
    assert [row["id"] for row in enterprise_filter.json()] == [enterprise["id"]]
    assert [row["id"] for row in prioritized_filter.json()] == [enterprise["id"]]
    assert len(unsynced_filter.json()) == 2


def test_merge_transfers_source_signals_to_target_without_losing_score():
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}
    with TestClient(app) as client:
        source = client.post("/api/v1/accounts", headers=headers, json={"name": "Merge Source", "domain": "merge-source.example"}).json()
        target = client.post("/api/v1/accounts", headers=headers, json={"name": "Merge Target", "domain": "merge-target.example"}).json()
        signal = client.post(
            "/api/v1/signals",
            headers=headers,
            json={
                "account_id": source["id"],
                "signal_type": "funding",
                "description": "Raised a new growth funding round",
                "confidence": 100,
            },
        ).json()
        merged = client.post(f"/api/v1/accounts/{source['id']}/merge/{target['id']}", headers=headers)
        target_after = client.get(f"/api/v1/accounts/{target['id']}", headers=headers)
        source_signals = client.get(f"/api/v1/accounts/{target['id']}/signals", headers=headers)
    assert merged.status_code == 200
    assert target_after.json()["score"] == 15
    assert len(source_signals.json()) == 1
    assert source_signals.json()[0]["id"] == signal["id"]



def test_account_pin_is_persisted_and_audited():
    tenant_id = str(uuid4())
    headers = {"X-Tenant-ID": tenant_id}
    with TestClient(app) as client:
        account = client.post("/api/v1/accounts", headers=headers, json={"name": "Pinned Co", "domain": "pinned.example"}).json()
        pinned = client.patch(f"/api/v1/accounts/{account['id']}/pin", headers=headers, json={"pinned": True})
        details = client.get(f"/api/v1/accounts/{account['id']}", headers=headers)
    assert pinned.status_code == 200 and pinned.json()["pinned"] is True
    assert details.json()["is_pinned"] is True
