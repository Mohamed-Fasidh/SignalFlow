import base64
import hashlib
import hmac
import json
import time
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.core.tenant import _decode_tenant_token
from app.core.config import settings


def _token(claims):
    enc = lambda value: base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    header = enc({"alg": "HS256", "typ": "JWT"})
    payload = enc(claims)
    message = f"{header}.{payload}".encode()
    signature = base64.urlsafe_b64encode(hmac.new(settings.secret_key.encode(), message, hashlib.sha256).digest()).decode().rstrip("=")
    return f"{header}.{payload}.{signature}"


def test_signed_tenant_token_resolves():
    tenant = uuid4()
    token = _token({"tenant_id": str(tenant), "iat": int(time.time()), "exp": int(time.time()) + 300})
    assert _decode_tenant_token(token) == tenant


def test_invalid_token_rejected():
    with pytest.raises(HTTPException) as error:
        _decode_tenant_token("not-a-token")
    assert error.value.status_code == 401


def test_expired_token_rejected():
    token = _token({"tenant_id": str(uuid4()), "iat": int(time.time()) - 600, "exp": int(time.time()) - 1})
    with pytest.raises(HTTPException):
        _decode_tenant_token(token)


def test_tenant_header_is_not_accepted_outside_local_modes(monkeypatch):
    from app.core.tenant import tenant_dependency
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(HTTPException) as error:
        tenant_dependency(credentials=None, x_tenant_id=uuid4())
    assert error.value.status_code == 401


def test_token_issuer_and_audience_are_enforced(monkeypatch):
    from app.core.config import settings
    tenant = uuid4()
    monkeypatch.setattr(settings, "jwt_issuer", "https://identity.example")
    monkeypatch.setattr(settings, "jwt_audience", "signalflow-api")
    claims = {"tenant_id": str(tenant), "iat": int(time.time()), "exp": int(time.time()) + 300,
              "iss": "https://identity.example", "aud": ["signalflow-api"]}
    assert _decode_tenant_token(_token(claims)) == tenant
    claims["iss"] = "https://attacker.example"
    with pytest.raises(HTTPException):
        _decode_tenant_token(_token(claims))
    claims["iss"] = "https://identity.example"
    claims["aud"] = "other-api"
    with pytest.raises(HTTPException):
        _decode_tenant_token(_token(claims))
