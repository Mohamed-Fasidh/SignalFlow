"""Add account pin state."""
from alembic import op
import sqlalchemy as sa

revision = "0006_account_pins"
down_revision = "0005_research_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("accounts", "is_pinned")
