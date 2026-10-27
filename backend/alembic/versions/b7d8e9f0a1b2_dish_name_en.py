"""dishes.name_en (tên món tiếng Anh)

Revision ID: b7d8e9f0a1b2
Revises: a1c2e3f4b5d6
Create Date: 2026-10-27 23:45:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7d8e9f0a1b2'
down_revision = 'a1c2e3f4b5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Giá trị được điền khi chạy `python -m app.seed` (upsert idempotent từ seed/dishes.json)
    op.add_column('dishes', sa.Column('name_en', sa.String(length=160), nullable=True))


def downgrade() -> None:
    op.drop_column('dishes', 'name_en')
