"""dishes.log_sides (phần ăn kèm điển hình khi ghi nhật ký món)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-10-28 06:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Giá trị được điền khi chạy `python -m app.seed` (upsert idempotent từ seed/dishes.json)
    op.add_column('dishes', sa.Column('log_sides', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('dishes', 'log_sides')
