"""
Initial database schema

Revision ID: 001
Revises: None
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 年级
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(20), unique=True, comment="初一级/初二级/初三级"),
        sa.Column("sort_order", sa.Integer(), default=0),
    )
    # 学年学期
    op.create_table(
        "semesters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year_start", sa.Integer(), nullable=False),
        sa.Column("semester", sa.String(10), nullable=False, comment="第一学期/第二学期"),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("is_current", sa.Boolean(), default=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(10), default="未开始"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("year_start", "semester"),
    )
    # 科目
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(20), unique=True),
        sa.Column("full_mark", sa.Float(), default=100),
        sa.Column("pass_line", sa.Float(), default=60),
        sa.Column("good_line", sa.Float(), default=80),
        sa.Column("excellent_line", sa.Float(), default=90),
        sa.Column("low_line", sa.Float(), default=30),
        sa.Column("sort_order", sa.Integer(), default=0),
    )
    # 班级
    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grade_id", sa.Integer(), sa.ForeignKey("grades.id"), nullable=False),
        sa.Column("name", sa.String(10)),
        sa.Column("head_teacher", sa.String(20), default=""),
        sa.Column("class_type", sa.String(20), default=""),
        sa.Column("room", sa.String(20), default=""),
        sa.UniqueConstraint("grade_id", "name"),
    )
    # 学生
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("name", sa.String(20), index=True),
        sa.Column("former_name", sa.String(20), default=""),
        sa.Column("student_no", sa.String(10), default=""),
        sa.Column("student_code", sa.String(30), default=""),
        sa.Column("id_card", sa.String(20), default=""),
        sa.Column("gender", sa.String(4), default=""),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("phone", sa.String(20), default=""),
        sa.Column("address", sa.String(100), default=""),
        sa.Column("enroll_year", sa.Integer(), default=0),
        sa.Column("exam_no", sa.String(20), default=""),
        sa.Column("ethnicity", sa.String(10), default=""),
        sa.Column("native_place", sa.String(30), default=""),
        sa.Column("boarding", sa.String(10), default="走读"),
        sa.Column("status", sa.String(10), default="在校"),
        sa.Column("note", sa.Text(), default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("class_id", "name", name="uq_student_class_name"),
    )
    op.create_index("idx_student_status", "students", ["status"])
    # 教师
    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(20), unique=True),
        sa.Column("phone", sa.String(20), default=""),
        sa.Column("title", sa.String(20), default=""),
        sa.Column("note", sa.Text(), default=""),
    )
    # 班级-科目-教师（任课）
    op.create_table(
        "class_subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("semester_id", sa.Integer(), sa.ForeignKey("semesters.id"), nullable=False),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("teacher_id", sa.Integer(), sa.ForeignKey("teachers.id"), nullable=True),
        sa.UniqueConstraint("semester_id", "class_id", "subject_id"),
    )
    # 考试
    op.create_table(
        "exams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("semester_id", sa.Integer(), sa.ForeignKey("semesters.id"), nullable=False),
        sa.Column("name", sa.String(30)),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("grade_id", sa.Integer(), sa.ForeignKey("grades.id"), nullable=True),
        sa.Column("note", sa.Text(), default=""),
        sa.UniqueConstraint("semester_id", "name", "grade_id"),
    )
    # 成绩
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "exam_id", sa.Integer(), sa.ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=True, comment="NULL=缺考"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("exam_id", "student_id", "subject_id"),
    )
    op.create_index("idx_scores_exam", "scores", ["exam_id"])
    op.create_index("idx_scores_student", "scores", ["student_id"])
    op.create_index("idx_scores_exam_subj", "scores", ["exam_id", "subject_id"])
    # 年级-科目关联
    op.create_table(
        "grade_subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grade_id", sa.Integer(), sa.ForeignKey("grades.id")),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id")),
        sa.Column("sort_order", sa.Integer(), default=0),
        sa.UniqueConstraint("grade_id", "subject_id"),
    )
    # 考试科目设置
    op.create_table(
        "exam_subject_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id")),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id")),
        sa.Column("full_mark", sa.Float(), default=100),
        sa.Column("pass_line", sa.Float(), default=60),
        sa.Column("good_line", sa.Float(), default=80),
        sa.Column("excellent_line", sa.Float(), default=90),
        sa.Column("low_line", sa.Float(), default=30),
        sa.UniqueConstraint("exam_id", "subject_id"),
    )
    # 学籍变动
    op.create_table(
        "student_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE")),
        sa.Column("semester_id", sa.Integer(), sa.ForeignKey("semesters.id"), nullable=True),
        sa.Column("move_type", sa.String(10), comment="转班/休学/复学/退学/毕业/转入/转出"),
        sa.Column("move_date", sa.Date(), nullable=True),
        sa.Column("from_class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=True),
        sa.Column("to_class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=True),
        sa.Column("reason", sa.Text(), default=""),
        sa.Column("operator", sa.String(20), default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_movements_student", "student_movements", ["student_id"])
    # 系统设置
    op.create_table(
        "settings",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("value", sa.Text(), default=""),
    )


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("student_movements")
    op.drop_table("exam_subject_settings")
    op.drop_table("grade_subjects")
    op.drop_table("scores")
    op.drop_table("exams")
    op.drop_table("class_subjects")
    op.drop_table("teachers")
    op.drop_table("students")
    op.drop_table("classes")
    op.drop_table("subjects")
    op.drop_table("semesters")
    op.drop_table("grades")
