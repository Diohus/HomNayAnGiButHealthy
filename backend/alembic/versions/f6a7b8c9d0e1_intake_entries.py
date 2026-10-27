"""intake_entries (nhật ký đã ăn)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-28 10:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('intake_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('slot', sa.String(length=16), nullable=False),
    sa.Column('food_code', sa.String(length=64), nullable=False),
    sa.Column('grams', sa.Float(), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_intake_entries_user_id'), 'intake_entries', ['user_id'], unique=False)
    op.create_index(op.f('ix_intake_entries_day'), 'intake_entries', ['day'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_intake_entries_day'), table_name='intake_entries')
    op.drop_index(op.f('ix_intake_entries_user_id'), table_name='intake_entries')
    op.drop_table('intake_entries')
