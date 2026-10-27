"""refresh_tokens.rotated_at (khoảng ân hạn khi refresh song song)

Revision ID: a1c2e3f4b5d6
Revises: f35083266e75
Create Date: 2026-10-27 23:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1c2e3f4b5d6'
down_revision = 'f35083266e75'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('refresh_tokens', sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('refresh_tokens', 'rotated_at')
