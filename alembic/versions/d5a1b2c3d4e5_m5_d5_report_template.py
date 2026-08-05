"""M5-D5: report_templates 报表模板表

Revision ID: d5a1b2c3d4e5
Revises: c2a1b2c3d4e5
Create Date: 2026-08-05

报表模板管理：名称/类型/文件路径/版本/变量列表。
版本管理：同名模板多版本 (name, version) 唯一，旧版本保留可回滚。
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5a1b2c3d4e5"
down_revision: str | None = "c2a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 幂等：已存在则跳过
    bind = op.get_bind()
    if not bind.dialect.has_table(bind, "report_templates"):
        op.create_table(
            "report_templates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("template_type", sa.String(20), nullable=False, server_default="excel"),
            sa.Column("file_path", sa.String(300), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("variables", sa.Text(), nullable=True),
            sa.Column("description", sa.String(300), nullable=True, server_default=""),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("1")),
            sa.Column("created_by", sa.String(50), nullable=True, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("name", "version", name="uq_report_template_version"),
        )
        op.create_index("idx_report_template_name", "report_templates", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_report_template_name", "report_templates")
    op.drop_table("report_templates")
