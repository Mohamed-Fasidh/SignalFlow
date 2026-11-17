from collections.abc import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import settings


class Base(DeclarativeBase):
    pass


_is_sqlite = settings.database_url.startswith("sqlite")
_engine_options = {"pool_pre_ping": True}
if _is_sqlite:
    _engine_options.update(poolclass=StaticPool, connect_args={"check_same_thread": False})
else:
    _engine_options.update(pool_size=5, max_overflow=10, pool_recycle=1800)
engine = create_engine(settings.database_url, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _set_postgres_tenant_context(session: Session, transaction, connection) -> None:
    """Set transaction-local RLS context for every transaction in a request session."""
    tenant_id = session.info.get("tenant_id")
    if tenant_id is not None and connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
