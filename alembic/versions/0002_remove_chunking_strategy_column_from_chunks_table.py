from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

EMBEDDING_DIMENSION = 1536  # tied to embedder config; see ADR-005


def upgrade() -> None:
    op.drop_column("chunks", "chunking_strategy")


def downgrade() -> None:
    op.add_column("chunks", sa.Column("chunking_strategy", sa.Text(), nullable=False))