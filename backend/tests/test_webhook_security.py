import hashlib
import hmac
import pytest
from fastapi import HTTPException
from app.integrations.webhook_security import verify_hmac_sha256


def test_valid_signature():
    body = b'{"event":"company.updated"}'
    secret = "test-secret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    verify_hmac_sha256(body, "sha256=" + sig, secret)


def test_invalid_signature_rejected():
    with pytest.raises(HTTPException):
        verify_hmac_sha256(b"payload", "bad", "secret")


def test_hubspot_v3_signature_valid(monkeypatch):
    import base64
    import time
    from unittest.mock import Mock
    from app.integrations.webhook_security import verify_hubspot_v3
    from urllib.parse import quote, unquote

    request = Mock()
    request.url = "https://example.test/api/v1/webhooks/hubspot"
    request.method = "POST"
    body = b'{"eventId":123}'
    timestamp = str(int(time.time() * 1000))
    uri = quote(unquote(str(request.url)), safe=":/")
    source = request.method + uri + body.decode() + timestamp
    digest = hmac.new(b"client-secret", source.encode(), hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode()
    verify_hubspot_v3(request, body, "client-secret", signature, timestamp)


def test_hubspot_v3_rejects_stale_timestamp():
    from unittest.mock import Mock
    from app.integrations.webhook_security import verify_hubspot_v3
    from fastapi import HTTPException

    request = Mock()
    request.url = "https://example.test/webhook"
    request.method = "POST"
    with pytest.raises(HTTPException) as error:
        verify_hubspot_v3(request, b"{}", "secret", "bad", "1")
    assert error.value.status_code == 401
