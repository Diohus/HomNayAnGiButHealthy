"""health_limits (giới hạn sức khỏe do người dùng cung cấp) thay expert_confirmations

Chuyển dữ liệu: mỗi dòng expert_confirmations ⇒ một dòng health_limits (source="manual"); payload mã hóa giữ
nguyên (ExpertLimits là tập con của HealthLimits). Downgrade làm ngược lại: chỉ chuyển dòng có condition_code,
và bỏ các chỉ số mới (carb_g_max, fat_g_max) khỏi payload — cần HEALTH_DATA_KEY để giải mã/mã hóa lại.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-28 02:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

NEW_FIELDS = ("carb_g_max", "fat_g_max")


def upgrade() -> None:
    op.create_table('health_limits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('condition_code', sa.String(length=32), nullable=True),
    sa.Column('encrypted_payload', sa.LargeBinary(), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'condition_code')
    )
    op.create_index(op.f('ix_health_limits_user_id'), 'health_limits', ['user_id'], unique=False)
    op.execute(
        "INSERT INTO health_limits (user_id, condition_code, encrypted_payload, source, confirmed_at) "
        "SELECT user_id, condition_code, encrypted_limits, 'manual', confirmed_at FROM expert_confirmations"
    )
    op.drop_index(op.f('ix_expert_confirmations_user_id'), table_name='expert_confirmations')
    op.drop_table('expert_confirmations')


def downgrade() -> None:
    op.create_table('expert_confirmations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('condition_code', sa.String(length=32), nullable=False),
    sa.Column('encrypted_limits', sa.LargeBinary(), nullable=False),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'condition_code')
    )
    op.create_index(op.f('ix_expert_confirmations_user_id'), 'expert_confirmations', ['user_id'], unique=False)
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT user_id, condition_code, encrypted_payload, confirmed_at FROM health_limits "
        "WHERE condition_code IS NOT NULL")).fetchall()
    if rows:
        from app.core.crypto import get_cipher  # chỉ cần khóa khi thật sự có dữ liệu

        cipher = get_cipher()
        # cột không khai kiểu: chép nguyên giá trị thô đã đọc (Uuid/DateTime lưu khác nhau giữa SQLite và Postgres)
        expert = sa.table("expert_confirmations", sa.column("user_id"), sa.column("condition_code"),
                         sa.column("encrypted_limits", sa.LargeBinary()),
                         sa.column("confirmed_at"))
        for user_id, cond, payload, confirmed_at in rows:
            limits = {k: v for k, v in cipher.decrypt(payload).items() if k not in NEW_FIELDS}
            if any(v is not None for v in limits.values()):  # mô hình cũ cần ít nhất một giới hạn
                conn.execute(expert.insert().values(user_id=user_id, condition_code=cond,
                                                   encrypted_limits=cipher.encrypt(limits),
                                                   confirmed_at=confirmed_at))
    op.drop_index(op.f('ix_health_limits_user_id'), table_name='health_limits')
    op.drop_table('health_limits')
