"""Tenant row-level security and idempotent webhook inbox."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_rls_webhooks"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default="hubspot"),
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "provider", "event_id", name="uq_webhook_tenant_provider_event"),
    )
    op.create_index("ix_webhook_events_tenant_id", "webhook_events", ["tenant_id"])
    op.create_index("ix_webhook_tenant_received", "webhook_events", ["tenant_id", "received_at"])
    # App role must not be a superuser or have BYPASSRLS. In production, use a separate
    # migration owner and a restricted runtime role.
    for table in ("accounts", "buying_signals", "audit_events", "webhook_events"):
        op.execute(sa.text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
        policy = (
            f"CREATE POLICY tenant_isolation ON \"{table}\" "
            "USING (tenant_id::text = current_setting('app.current_tenant', true)) "
            "WITH CHECK (tenant_id::text = current_setting('app.current_tenant', true))"
        )
        op.execute(sa.text(policy))


def downgrade():
    for table in ("webhook_events", "audit_events", "buying_signals", "accounts"):
        op.execute(sa.text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
        op.execute(sa.text(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY'))
    op.drop_index("ix_webhook_tenant_received", table_name="webhook_events")
    op.drop_index("ix_webhook_events_tenant_id", table_name="webhook_events")
    op.drop_table("webhook_events")
