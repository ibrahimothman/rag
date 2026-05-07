from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None



def upgrade() -> None:
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("failure", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("retry_policy", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "ux_jobs_document_id", 
        "ingestion_jobs", 
        ["document_id"],
        unique=True,
    )
    op.create_index("ix_jobs_stage", "ingestion_jobs", ["stage"])


def downgrade() -> None:
    op.drop_index("ux_jobs_document_id", table_name="ingestion_jobs")
    op.drop_index("ix_jobs_stage", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
