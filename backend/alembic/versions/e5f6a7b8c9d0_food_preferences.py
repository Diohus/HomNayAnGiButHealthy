"""food_preferences (món / nguyên liệu không thích)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-28 03:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('food_preferences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=8), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'kind', 'code')
    )
    op.create_index(op.f('ix_food_preferences_user_id'), 'food_preferences', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_food_preferences_user_id'), table_name='food_preferences')
    op.drop_table('food_preferences')
