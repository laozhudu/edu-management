"""baseline_v2: create_all 基线（与模型同步，SQLite 兼容）

Revision ID: 090a005a9f30
Revises: a1b2c3d4e5f6
Create Date: 2026-08-03 13:24:54.771594

说明：
- 本迁移为"基线对齐"：将当前所有模型的表结构固化为基线。
- upgrade 用 Base.metadata.create_all()（幂等，只补缺失表/列，与模型永远同步）；
  downgrade 用 drop_all() 清空全部表。
- 此后所有表结构变更一律新增迁移（alembic revision --autogenerate），禁止手写 ALTER。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# 导入模型元数据（触发全部表注册）
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from edu_system.models import Base  # noqa: E402

# revision identifiers, used by Alembic.
revision: str = '090a005a9f30'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """幂等补齐：创建模型定义的全部缺失表（已有表不动）"""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """回滚：删除全部表（危险操作，仅演练/测试库使用）"""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
