"""Add explicit account tier and CRM synchronization timestamp."""
from alembic import op
import sqlalchemy as sa

revision = "0004_account_filters"
down_revision = "0003_workspace_features"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("tier", sa.String(length=20), nullable=False, server_default="unknown"))
    op.add_column("accounts", sa.Column("crm_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("accounts", "crm_synced_at")
    op.drop_column("accounts", "tier")
