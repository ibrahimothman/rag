from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIMENSION = 1536  # tied to embedder config; see ADR-005


def upgrade() -> None:
    # Ensure the pgvector extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSION), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("chunking_strategy", sa.Text(), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    # Vector similarity index — IVFFlat is reasonable to start, later we can try HNSW
    op.execute(
        "CREATE INDEX ix_chunks_embedding ON chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")