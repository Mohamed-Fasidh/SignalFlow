from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SignalFlow AI"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "unsafe-local-only-change-me"
    webhook_signing_secret: str = "unsafe-local-webhook-secret"
    database_url: str = "postgresql+psycopg://signalflow:signalflow_dev_only@localhost:5432/signalflow"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    access_token_expire_minutes: int = 30
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    ai_model: str | None = None
    hubspot_private_app_token: str | None = None
    hubspot_client_secret: str | None = None
    hubspot_webhook_tenant_id: str | None = None
    hubspot_demo_tenant_id: str | None = None
    max_request_body_bytes: int = 1048576

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
