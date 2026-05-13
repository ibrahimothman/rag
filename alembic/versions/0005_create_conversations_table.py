from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

#TODO: best practices for timestamps?

def upgrade() -> None:
    op.create_table(
        'conversations',
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
    )

    op.create_table(
        'conversation_messages',
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('grounding_quality', sa.Text(), nullable=True),
        sa.Column('citations', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        
    )

    op.create_index(
        'ix_messages_conversation_id', 
        'conversation_messages', 
        ['conversation_id'], 
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_messages_conversation_id', table_name='conversation_messages')
    op.drop_table('conversation_messages')
    op.drop_table('conversations')