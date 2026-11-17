import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine
from app.api.routes import router

logging.basicConfig(level=settings.log_level)
app = FastAPI(title=settings.app_name, version="0.3.0",
              description="GTM intelligence and revenue automation API",
              docs_url="/docs" if settings.app_env != "production" else None,
              redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Tenant-ID",
        "X-Webhook-Signature",
        "X-HubSpot-Signature-v3",
        "X-HubSpot-Request-Timestamp",
    ],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def security_and_request_context(request: Request, call_next):
    """Apply lightweight API edge protections and a traceable request identifier."""
    supplied_id = request.headers.get("X-Request-ID", "")
    # Accept only simple opaque identifiers; never reflect arbitrary header content.
    request_id = supplied_id if 1 <= len(supplied_id) <= 64 and supplied_id.replace("-", "").isalnum() else uuid.uuid4().hex
    request.state.request_id = request_id
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.max_request_body_bytes:
                from fastapi.responses import JSONResponse
                response = JSONResponse(status_code=413, content={"detail": "Request body too large", "request_id": request_id})
            else:
                response = await call_next(request)
        except ValueError:
            from fastapi.responses import JSONResponse
            response = JSONResponse(status_code=400, content={"detail": "Invalid Content-Length", "request_id": request_id})
    else:
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.app_env.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health/live", tags=["health"])
def liveness():
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        from redis import Redis
        Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2).ping()
        return {"status": "ready", "database": "ok", "redis": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


if settings.app_env.lower() == "production":
    insecure_prefixes = ("unsafe-", "replace-", "change-me", "changeme")
    if len(settings.secret_key) < 32 or settings.secret_key.lower().startswith(insecure_prefixes):
        raise RuntimeError("SECRET_KEY must be a strong, unique value in production")
    if len(settings.webhook_signing_secret) < 32 or settings.webhook_signing_secret.lower().startswith(insecure_prefixes):
        raise RuntimeError("WEBHOOK_SIGNING_SECRET must be a strong, unique value in production")
    if not settings.jwt_issuer or not settings.jwt_audience:
        raise RuntimeError("JWT_ISSUER and JWT_AUDIENCE must be configured in production")
    if not settings.cors_origin_list or "*" in settings.cors_origin_list:
        raise RuntimeError("CORS_ORIGINS must contain explicit trusted origins in production")

app.include_router(router, prefix=settings.api_v1_prefix)
