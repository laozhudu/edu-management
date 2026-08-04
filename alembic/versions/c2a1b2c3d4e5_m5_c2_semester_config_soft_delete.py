"""M5-C2: semester_configs 软删除字段 + 唯一约束改 (semester_id, key, version)

Revision ID: c2a1b2c3d4e5
Revises: 21cddd8e2a52
Create Date: 2026-08-05

软删除保留历史版本行，支持配置版本回滚追溯。
唯一约束从 (semester_id, key) 改为 (semester_id, key, version)，
使同 key 多版本可共存（旧版本软删除后仍保留历史）。
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2a1b2c3d4e5"
down_revision: str | None = "21cddd8e2a52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 幂等：已存在则跳过（兼容 init_db 已建列的场景）
    bind = op.get_bind()
    cols = [c[1] for c in bind.execute(sa.text("PRAGMA table_info(semester_configs)"))]
    if "is_deleted" not in cols:
        op.add_column(
            "semester_configs",
            sa.Column("is_deleted", sa.Boolean(), nullable=True, server_default=sa.text("0")),
        )
    if "deleted_at" not in cols:
        op.add_column(
            "semester_configs",
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
    # 唯一约束改为 (semester_id, key, version)，支持同 key 多版本
    for constraint in bind.execute(sa.text("PRAGMA index_list(semester_configs)")).fetchall():
        if constraint[3] == 1:  # unique index
            op.drop_index(constraint[1], table_name="semester_configs", if_exists=True)
    op.create_unique_constraint(
        "uq_semester_config_version",
        "semester_configs",
        ["semester_id", "key", "version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_semester_config_version", "semester_configs")
    op.create_unique_constraint("uq_semester_config", "semester_configs", ["semester_id", "key"])
    op.drop_column("semester_configs", "deleted_at")
    op.drop_column("semester_configs", "is_deleted")
