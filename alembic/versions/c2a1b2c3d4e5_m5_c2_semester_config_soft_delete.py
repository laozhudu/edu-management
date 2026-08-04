"""M5-C2: semester_config_history 版本快照表

Revision ID: c2a1b2c3d4e5
Revises: 21cddd8e2a52
Create Date: 2026-08-05

配置版本回滚方案：
- semester_configs 保持 (semester_id, key) 唯一存当前值（不改约束，
  回避 SQLite batch 迁移与跨表视图冲突）
- 新增 semester_config_history 快照表存每次写入/回滚版本（key/value/version），
  回滚时从历史读取目标版本覆盖当前值
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2a1b2c3d4e5"
down_revision: str | None = "21cddd8e2a52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 版本快照表（幂等：已存在则跳过）
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "semester_config_history"):
        op.create_table(
            "semester_config_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("semester_id", sa.Integer(), nullable=False, index=True),
            sa.Column("key", sa.String(50), nullable=False),
            sa.Column("value", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(20), nullable=False, server_default="SAVE"),
            sa.Column("operator", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_config_history_semester_version",
            "semester_config_history",
            ["semester_id", "version"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_config_history_semester_version", "semester_config_history")
    op.drop_table("semester_config_history")
