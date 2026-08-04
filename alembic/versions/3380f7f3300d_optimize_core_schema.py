"""optimize_core_schema

Revision ID: 3380f7f3300d
Revises: 001
Create Date: 2026-07-29

优化核心 schema：补全约束、索引、软删、触发器
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3380f7f3300d"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. 给所有业务表添加 deleted_at 软删字段（不影响现有数据）
    # ============================================================
    for table in [
        "grades",
        "semesters",
        "subjects",
        "classes",
        "students",
        "teachers",
        "class_subjects",
        "exams",
        "scores",
        "grade_subjects",
        "exam_subject_settings",
        "student_movements",
        "classrooms",
        "roles",
    ]:
        try:
            op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        except Exception:
            pass  # 可能已存在或表不存在

    # 补全 teachers.staff_no
    try:
        op.add_column("teachers", sa.Column("staff_no", sa.String(20), nullable=True))
    except Exception:
        pass  # 可能已存在
    op.create_index("uq_teachers_staff_no", "teachers", ["staff_no"], unique=True)

    # ============================================================
    # 2. 关键唯一约束（SQLite 不支持 WHERE 子句的部分索引，
    #    这里用普通唯一索引；业务层配合 deleted_at 过滤）
    # ============================================================
    # 学生：学籍号唯一、身份证非空时唯一
    op.create_index("uq_students_student_code", "students", ["student_code"], unique=True)
    op.create_index("uq_students_id_card", "students", ["id_card"], unique=True)

    # 班级：年级+班号唯一（已存在 uq_class_grade_name，补全索引）
    try:
        op.create_index("uq_classes_grade_name", "classes", ["grade_id", "name"], unique=True)
    except Exception:
        pass

    # ============================================================
    # 3. CHECK 约束（SQLite 3.38+ 支持 CREATE TABLE 时，但 ALTER TABLE
    #    不直接支持 ADD CHECK；这里用 TRIGGER 模拟）
    # ============================================================
    # 学生性别
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS chk_students_gender
        BEFORE INSERT ON students
        FOR EACH ROW BEGIN
            SELECT CASE
                WHEN NEW.gender NOT IN ('男', '女') THEN
                    RAISE(ABORT, 'gender must be 男 or 女')
            END;
        END;
    """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS chk_students_gender_upd
        BEFORE UPDATE OF gender ON students
        FOR EACH ROW BEGIN
            SELECT CASE
                WHEN NEW.gender NOT IN ('男', '女') THEN
                    RAISE(ABORT, 'gender must be 男 or 女')
            END;
        END;
    """
    )

    # 学生状态
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS chk_students_status
        BEFORE INSERT ON students
        FOR EACH ROW BEGIN
            SELECT CASE
                WHEN NEW.status NOT IN ('在校', '休学', '复学', '退学', '转学', '毕业') THEN
                    RAISE(ABORT, 'invalid status')
            END;
        END;
    """
    )

    # 成绩分值范围
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS chk_scores_range
        BEFORE INSERT ON scores
        FOR EACH ROW BEGIN
            SELECT CASE
                WHEN NEW.score IS NOT NULL AND (NEW.score < 0 OR NEW.score > 150) THEN
                    RAISE(ABORT, 'score must be 0-150')
            END;
        END;
    """
    )

    # ============================================================
    # 4. 关键复合索引（查询性能）
    # ============================================================
    # 成绩：考试+班级+科目 → 班级排名查询
    op.create_index(
        "ix_scores_exam_class_subject", "scores", ["exam_id", "student_id", "subject_id"]
    )

    # 成绩：学生+考试 → 学生历史成绩
    op.create_index("ix_scores_student_exam", "scores", ["student_id", "exam_id"])

    # 学籍变动：学生+日期降序
    op.create_index("ix_movements_student_date", "student_movements", ["student_id", "move_date"])

    # 学生：班级+状态
    op.create_index("ix_students_class_status", "students", ["class_id", "status"])

    # 学生：入学年份（考号生成用）
    op.create_index("ix_students_enroll_year", "students", ["enroll_year"])

    # ============================================================
    # 5. 补全外键级联（SQLite 需重建表，这里仅记录意图，
    #    实际级联已在 001 中定义 ondelete='CASCADE'）
    # ============================================================

    # ============================================================
    # 6. 更新时间触发器（updated_at 自动维护）
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
        "chk_students_gender",
        "chk_students_gender_upd",
        "chk_students_status",
        "chk_scores_range",
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
        "uq_students_student_code",
        "uq_students_id_card",
        "uq_teachers_staff_no",
        "uq_classes_grade_name",
        "ix_scores_exam_class_subject",
        "ix_scores_student_exam",
        "ix_movements_student_date",
        "ix_students_class_status",
        "ix_students_enroll_year",
    ]
    for idx in indexes:
        try:
            op.drop_index(idx)
        except Exception:
            pass

    # 删除字段
    for table in [
        "grades",
        "semesters",
        "subjects",
        "classes",
        "students",
        "teachers",
        "class_subjects",
        "exams",
        "scores",
        "grade_subjects",
        "exam_subject_settings",
        "student_movements",
        "classrooms",
        "roles",
    ]:
        try:
            op.drop_column(table, "deleted_at")
        except Exception:
            pass

    try:
        op.drop_column("teachers", "staff_no")
    except Exception:
        pass
