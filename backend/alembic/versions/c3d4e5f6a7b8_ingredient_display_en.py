"""ingredients.display_en (tên hiển thị tiếng Anh ngắn)

Revision ID: c3d4e5f6a7b8
Revises: b7d8e9f0a1b2
Create Date: 2026-10-28 00:10:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Giá trị được điền khi chạy `python -m app.seed` (upsert idempotent từ seed/ingredients.json)
    op.add_column('ingredients', sa.Column('display_en', sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column('ingredients', 'display_en')
