"""add_core_entity_fields

Revision ID: 79faf3995363
Revises: 3380f7f3300d
Create Date: 2026-07-29

核心实体补字段：students/classes/teachers/exams/subjects 等
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "79faf3995363"
down_revision = "3380f7f3300d"
branch_labels = None
depends_on = None


def column_exists(conn, table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    result = conn.execute(sa.text(f"PRAGMA table_info({table_name})"))
    return any(row[1] == column_name for row in result.fetchall())


def upgrade() -> None:
    conn = op.get_bind()

    # ============================================================
    # 1. students 表新增字段（deleted_at 已存在）
    # ============================================================
    if not column_exists(conn, "students", "photo_hash"):
        op.add_column(
            "students",
            sa.Column("photo_hash", sa.String(64), nullable=True, comment="照片去重哈希"),
        )
    if not column_exists(conn, "students", "profile_completeness"):
        op.add_column(
            "students",
            sa.Column(
                "profile_completeness", sa.Integer(), server_default="0", comment="档案完整度0-100"
            ),
        )
    if not column_exists(conn, "students", "entry_type"):
        op.add_column(
            "students",
            sa.Column(
                "entry_type", sa.String(10), server_default="new", comment="new/transfer/returning"
            ),
        )
    if not column_exists(conn, "students", "updated_at"):
        op.add_column(
            "students", sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间")
        )

    # ============================================================
    # 2. classes 表新增字段（deleted_at 已存在）
    # ============================================================
    if not column_exists(conn, "classes", "head_teacher_id"):
        op.add_column(
            "classes", sa.Column("head_teacher_id", sa.Integer(), nullable=True, comment="班主任FK")
        )
    if not column_exists(conn, "classes", "capacity"):
        op.add_column(
            "classes", sa.Column("capacity", sa.Integer(), server_default="50", comment="最大容量")
        )
    if not column_exists(conn, "classes", "is_active"):
        op.add_column(
            "classes", sa.Column("is_active", sa.Boolean(), server_default="1", comment="是否在用")
        )
    if not column_exists(conn, "classes", "updated_at"):
        op.add_column(
            "classes", sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间")
        )
    op.create_index("ix_classes_grade_active", "classes", ["grade_id", "is_active"])

    # ============================================================
    # 3. teachers 表新增字段（deleted_at 已存在）
    # ============================================================
    if not column_exists(conn, "teachers", "status"):
        op.add_column(
            "teachers",
            sa.Column("status", sa.String(10), server_default="在职", comment="在职/离职/退休"),
        )
    if not column_exists(conn, "teachers", "staff_no"):
        op.add_column(
            "teachers", sa.Column("staff_no", sa.String(20), nullable=True, comment="工号")
        )
    if not column_exists(conn, "teachers", "updated_at"):
        op.add_column(
            "teachers", sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间")
        )
    # 工号唯一索引（SQLite 用索引代替约束）
    try:
        op.create_index("uq_teachers_staff_no", "teachers", ["staff_no"], unique=True)
    except Exception:
        pass

    # ============================================================
    # 4. teacher_subjects 关联表（新增）
    # ============================================================
    try:
        op.create_table(
            "teacher_subjects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("teacher_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("grade_id", sa.Integer(), nullable=True),
            sa.UniqueConstraint(
                "teacher_id", "subject_id", "grade_id", name="uq_teacher_subj_grade"
            ),
        )
    except Exception:
        pass

    # ============================================================
    # 5. subjects 表新增字段
    # ============================================================
    if not column_exists(conn, "subjects", "credit"):
        op.add_column(
            "subjects", sa.Column("credit", sa.Float(), server_default="1.0", comment="学分")
        )
    if not column_exists(conn, "subjects", "weight"):
        op.add_column(
            "subjects", sa.Column("weight", sa.Float(), server_default="1.0", comment="排名权重")
        )
    if not column_exists(conn, "subjects", "is_core"):
        op.add_column(
            "subjects",
            sa.Column("is_core", sa.Boolean(), server_default="1", comment="是否核心科目"),
        )
    if not column_exists(conn, "subjects", "exam_type"):
        op.add_column(
            "subjects",
            sa.Column(
                "exam_type",
                sa.String(10),
                server_default="normal",
                comment="normal/midterm/final/mock",
            ),
        )

    # ============================================================
    # 6. exams 表新增字段（deleted_at 已存在）
    # ============================================================
    if not column_exists(conn, "exams", "status"):
        op.add_column(
            "exams",
            sa.Column(
                "status", sa.String(10), server_default="draft", comment="draft/published/archived"
            ),
        )
    if not column_exists(conn, "exams", "exam_type"):
        op.add_column(
            "exams",
            sa.Column(
                "exam_type",
                sa.String(10),
                server_default="final",
                comment="midterm/final/monthly/mock",
            ),
        )
    if not column_exists(conn, "exams", "grade_start"):
        op.add_column("exams", sa.Column("grade_start", sa.Integer(), nullable=True))
    if not column_exists(conn, "exams", "grade_end"):
        op.add_column("exams", sa.Column("grade_end", sa.Integer(), nullable=True))
    if not column_exists(conn, "exams", "updated_at"):
        op.add_column(
            "exams", sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间")
        )
    op.create_index("ix_exams_semester_status", "exams", ["semester_id", "status"])

    # ============================================================
    # 7. scores 表新增字段（deleted_at 已存在）
    # ============================================================
    if not column_exists(conn, "scores", "rank_in_class"):
        op.add_column("scores", sa.Column("rank_in_class", sa.Integer(), nullable=True))
    if not column_exists(conn, "scores", "rank_in_grade"):
        op.add_column("scores", sa.Column("rank_in_grade", sa.Integer(), nullable=True))
    if not column_exists(conn, "scores", "percentile"):
        op.add_column(
            "scores", sa.Column("percentile", sa.Float(), nullable=True, comment="0-100百分位")
        )
    if not column_exists(conn, "scores", "is_makeup"):
        op.add_column("scores", sa.Column("is_makeup", sa.Boolean(), server_default="0"))
    if not column_exists(conn, "scores", "original_score"):
        op.add_column(
            "scores", sa.Column("original_score", sa.Float(), nullable=True, comment="补考前原始分")
        )
    if not column_exists(conn, "scores", "updated_at"):
        op.add_column(
            "scores", sa.Column("updated_at", sa.DateTime(), nullable=True, comment="更新时间")
        )
    op.create_index(
        "ix_scores_exam_class_rank", "scores", ["exam_id", "student_id", "rank_in_class"]
    )
    op.create_index("ix_scores_exam_grade_rank", "scores", ["exam_id", "rank_in_grade"])

    # ============================================================
    # 8. 审计日志表（新增）
    # ============================================================
    try:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("table_name", sa.String(50), nullable=False),
            sa.Column("record_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(10), nullable=False, comment="INSERT/UPDATE/DELETE"),
            sa.Column("old_values", sa.JSON(), nullable=True),
            sa.Column("new_values", sa.JSON(), nullable=True),
            sa.Column("operator", sa.String(20), nullable=True),
            sa.Column("ip", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_audit_table_record", "audit_logs", ["table_name", "record_id"])
        op.create_index("ix_audit_created", "audit_logs", ["created_at"])
    except Exception:
        pass

    # ============================================================
    # 9. 事件溯源表（新增）
    # ============================================================
    try:
        op.create_table(
            "domain_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("aggregate_id", sa.String(50), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), server_default="1"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_domain_events_aggregate", "domain_events", ["aggregate_id", "created_at"]
        )
    except Exception:
        pass

    # ============================================================
    # 10. 更新时间触发器（为新增 updated_at 字段的表）
    # ============================================================
    tables_with_updated = ["students", "teachers", "classes", "exams", "scores", "class_subjects"]
    for t in tables_with_updated:
        try:
            op.execute(
                f"""
                CREATE TRIGGER IF NOT EXISTS trg_{t}_updated_at
                AFTER UPDATE ON {t}
                FOR EACH ROW BEGIN
                    UPDATE {t} SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = OLD.id;
                END;
            """
            )
        except Exception:
            pass


def downgrade() -> None:
    # 删除触发器
    triggers = [
        "trg_students_updated_at",
        "trg_teachers_updated_at",
        "trg_classes_updated_at",
        "trg_exams_updated_at",
        "trg_scores_updated_at",
        "trg_class_subjects_updated_at",
    ]
    for trig in triggers:
        op.execute(f"DROP TRIGGER IF EXISTS {trig};")

    # 删除索引
    indexes = [
        "ix_audit_table_record",
        "ix_audit_created",
        "ix_domain_events_aggregate",
        "ix_scores_exam_class_rank",
        "ix_scores_exam_grade_rank",
        "ix_scores_exam_class",
        "ix_scores_student_exam",
        "ix_movements_student_date",
        "ix_students_class_status",
        "ix_students_enroll_year",
        "ix_classes_grade_active",
        "ix_exams_semester_status",
        "ix_scores_exam_class_rank",
        "ix_scores_exam_grade_rank",
        "uq_teachers_staff_no",
    ]
    for idx in indexes:
        try:
            op.drop_index(idx)
        except Exception:
            pass

    # 删除表
    op.drop_table("domain_events")
    op.drop_table("audit_logs")
    op.drop_table("teacher_subjects")

    # 注意：SQLite 不支持直接 DROP COLUMN，回滚时仅记录意图
    # 实际回滚需手工重建表或使用 batch_alter_table
