"""Optional PostgreSQL integration test; set TEST_POSTGRES_URL to a migrated test DB."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not configured")
def test_postgres_rls_hides_other_tenant_rows():
    engine = create_engine(os.environ["TEST_POSTGRES_URL"], pool_pre_ping=True)
    tenant_a, tenant_b = uuid4(), uuid4()
    account_id = uuid4()
    try:
        with engine.begin() as connection:
            role = connection.execute(text(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )).scalar_one()
            assert role is False, "RLS test must use a non-superuser role without BYPASSRLS"
            connection.execute(text("SELECT set_config('app.current_tenant', :tenant, true)"),
                               {"tenant": str(tenant_a)})
            connection.execute(text("""
                INSERT INTO accounts (id, tenant_id, name, domain, score, score_reasons, created_at, updated_at)
                VALUES (:id, :tenant, 'RLS test', 'rls-test.example', 0, '[]'::jsonb, now(), now())
            """), {"id": account_id, "tenant": tenant_a})
            connection.execute(text("SELECT set_config('app.current_tenant', :tenant, true)"),
                               {"tenant": str(tenant_b)})
            visible = connection.execute(text("SELECT count(*) FROM accounts WHERE id = :id"),
                                         {"id": account_id}).scalar_one()
            assert visible == 0
    finally:
        # Cleanup under the owning tenant context, even if the visibility assertion fails.
        with engine.begin() as connection:
            connection.execute(text("SELECT set_config('app.current_tenant', :tenant, true)"),
                               {"tenant": str(tenant_a)})
            connection.execute(text("DELETE FROM accounts WHERE id = :id"), {"id": account_id})
        engine.dispose()
