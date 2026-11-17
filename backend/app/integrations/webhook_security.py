import base64
import hashlib
import hmac
import time
from urllib.parse import quote, unquote
from fastapi import HTTPException, Request


def verify_hmac_sha256(raw_body: bytes, supplied_signature: str | None, secret: str) -> None:
    if not supplied_signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    candidate = supplied_signature.removeprefix("sha256=")
    if not hmac.compare_digest(expected, candidate):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def verify_hubspot_v3(request: Request, raw_body: bytes, client_secret: str,
                      signature: str | None, timestamp: str | None,
                      tolerance_seconds: int = 300) -> None:
    """Verify HubSpot's v3 request signature and reject stale/replayed timestamps."""
    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing HubSpot v3 signature headers")
    try:
        timestamp_ms = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid HubSpot signature timestamp") from exc
    if abs(int(time.time() * 1000) - timestamp_ms) > tolerance_seconds * 1000:
        raise HTTPException(status_code=401, detail="Expired HubSpot webhook signature")
    canonical_uri = quote(unquote(str(request.url)), safe=":/")
    source = request.method.upper() + canonical_uri + raw_body.decode("utf-8") + timestamp
    digest = hmac.new(client_secret.encode(), source.encode("utf-8"), hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid HubSpot v3 signature")
