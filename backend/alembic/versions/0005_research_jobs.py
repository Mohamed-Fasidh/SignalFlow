"""Persist asynchronous AI research jobs."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_research_jobs"
down_revision = "0004_account_filters"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", sa.String(160), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], ondelete="CASCADE", name="fk_research_account_tenant"),
    )
    op.create_index("ix_research_jobs_tenant_id", "research_jobs", ["tenant_id"])
    op.create_index("ix_research_tenant_created", "research_jobs", ["tenant_id", "created_at"])
    op.execute(sa.text('ALTER TABLE "research_jobs" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text('ALTER TABLE "research_jobs" FORCE ROW LEVEL SECURITY'))
    op.execute(sa.text("CREATE POLICY tenant_isolation ON research_jobs USING (tenant_id::text = current_setting('app.current_tenant', true)) WITH CHECK (tenant_id::text = current_setting('app.current_tenant', true))"))


def downgrade():
    op.execute(sa.text('DROP POLICY IF EXISTS tenant_isolation ON "research_jobs"'))
    op.execute(sa.text('ALTER TABLE "research_jobs" DISABLE ROW LEVEL SECURITY'))
    op.drop_index("ix_research_tenant_created", table_name="research_jobs")
    op.drop_index("ix_research_jobs_tenant_id", table_name="research_jobs")
    op.drop_table("research_jobs")
