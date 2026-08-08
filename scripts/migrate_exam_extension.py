"""
迁移：exams 表补充考试管理扩展列（幂等，独立脚本）

背景：Sprint 4.4.3 考试管理扩展（移植自 feat/sprint-4.4.3-exam-api）
现库由 create_all 管理（非 alembic 版本化），故用直接 ALTER TABLE 幂等补列。

用法: ./venv/bin/python scripts/migrate_exam_extension.py
"""

from pathlib import Path

import sqlalchemy as sa


def migrate(db_path: str = "data/school_data.db") -> None:
    """幂等地为 exams 表补充扩展列"""
    path = Path(db_path)
    if not path.exists():
        print(f"数据库不存在，跳过: {path}")
        return

    engine = sa.create_engine(f"sqlite:///{path}")
    inspector = sa.inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("exams")}
    print(f"exams 现有列: {sorted(existing)}")

    adds: list[tuple[str, sa.Column]] = []
    if "end_date" not in existing:
        adds.append(("end_date", sa.Column("end_date", sa.Date(), nullable=True)))
    if "status" not in existing:
        adds.append(
            (
                "status",
                sa.Column(
                    "status",
                    sa.String(20),
                    nullable=False,
                    server_default="draft",
                ),
            )
        )
    if "created_at" not in existing:
        adds.append(
            ("created_at", sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()))
        )
    if "updated_at" not in existing:
        adds.append(
            (
                "updated_at",
                sa.Column(
                    "updated_at",
                    sa.DateTime(),
                    server_default=sa.func.now(),
                    onupdate=sa.func.now(),
                ),
            )
        )

    if not adds:
        print("无需迁移，exams 列已齐全")
        return

    with engine.begin() as conn:
        for name, col in adds:
            conn.execute(
                sa.text(f"ALTER TABLE exams ADD COLUMN {name} {col.type.compile(engine.dialect)}")
            )
            print(f"+ 已添加列: {name}")

    # 回填存量行的 created_at/updated_at（server_default 不作用于新 ALTER 列）
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE exams SET created_at = COALESCE(created_at, datetime('now')), "
                "updated_at = COALESCE(updated_at, datetime('now')) "
                "WHERE created_at IS NULL OR updated_at IS NULL"
            )
        )
    print("已回填存量行 created_at/updated_at")
    print("迁移完成")


if __name__ == "__main__":
    migrate()
