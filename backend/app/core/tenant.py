"""Tenant identity resolution with signed HS256 JWT validation.

Local mode permits an explicit demo tenant header for development only. Other
modes require a signed JWT carrying tenant_id, iat and exp claims. In production,
configure the identity provider to issue this claim and use a managed secret store.
"""
import base64
import binascii
import hashlib
import hmac
import json
import time
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)


def _decode_tenant_token(token: str) -> UUID:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected = hmac.new(settings.secret_key.encode(), signing_input, hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature_part + "=" * (-len(signature_part) % 4))
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("bad signature")
        header = json.loads(base64.urlsafe_b64decode(header_part + "=" * (-len(header_part) % 4)))
        claims = json.loads(base64.urlsafe_b64decode(payload_part + "=" * (-len(payload_part) % 4)))
        if header.get("alg") != "HS256":
            raise ValueError("unsupported algorithm")
        now = int(time.time())
        issued_at = int(claims["iat"])
        expires_at = int(claims["exp"])
        if expires_at <= now or issued_at > now + 60 or expires_at <= issued_at:
            raise ValueError("expired or future token")
        if settings.jwt_issuer and claims.get("iss") != settings.jwt_issuer:
            raise ValueError("unexpected token issuer")
        if settings.jwt_audience:
            audience = claims.get("aud")
            audiences = audience if isinstance(audience, list) else [audience]
            if settings.jwt_audience not in audiences:
                raise ValueError("unexpected token audience")
        return UUID(str(claims["tenant_id"]))
    except (ValueError, KeyError, TypeError, AttributeError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc


def tenant_dependency(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_tenant_id: UUID | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID:
    if settings.app_env.lower() in {"local", "development", "test"} and x_tenant_id:
        return x_tenant_id
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    return _decode_tenant_token(credentials.credentials)


def get_tenant_db(tenant_id: UUID = Depends(tenant_dependency)):
    """Yield a DB session with transaction-local PostgreSQL RLS context."""
    from app.core.database import SessionLocal
    db = SessionLocal()
    db.info["tenant_id"] = tenant_id
    try:
        yield db
    finally:
        db.close()
