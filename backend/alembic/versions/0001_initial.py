"""Initial GTM schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(120)),
        sa.Column("employee_count", sa.Integer()),
        sa.Column("country", sa.String(2)),
        sa.Column("description", sa.Text()),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_reasons", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "domain", name="uq_account_tenant_domain"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_account_id_tenant"),
    )
    op.create_index("ix_accounts_tenant_score", "accounts", ["tenant_id", "score"])
    op.create_table(
        "buying_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_type", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("source_name", sa.String(120), nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], ondelete="CASCADE", name="fk_signal_account_tenant"),
    )
    op.create_index("ix_signals_account_type", "buying_signals", ["account_id", "signal_type"])
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("actor", sa.String(120), nullable=False, server_default="system"),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(80), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("audit_events")
    op.drop_index("ix_signals_account_type", table_name="buying_signals")
    op.drop_table("buying_signals")
    op.drop_index("ix_accounts_tenant_score", table_name="accounts")
    op.drop_table("accounts")
