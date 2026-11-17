"""Add account priority and soft-archived buying signals."""
from alembic import op
import sqlalchemy as sa

revision = "0003_workspace_features"
down_revision = "0002_rls_webhooks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("priority", sa.String(length=16), nullable=False, server_default="normal"))
    op.add_column("buying_signals", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("buying_signals", "archived_at")
    op.drop_column("accounts", "priority")
