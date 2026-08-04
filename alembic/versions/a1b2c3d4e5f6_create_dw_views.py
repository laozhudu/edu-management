"""
宽表物化视图 - 为报表查询提供预聚合数据
定时任务每夜刷新，报表查询直接读取视图，避免大 JOIN 阻塞主库
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "79faf3995363"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ============================================================
    # 1. 学生考试成绩事实表（物化视图）
    # ============================================================
    conn.execute(sa.text("DROP VIEW IF EXISTS v_fact_student_exam_score"))

    conn.execute(
        sa.text(
            """
        CREATE VIEW v_fact_student_exam_score AS
        SELECT 
            sc.id AS fact_id,
            s.id AS student_id,
            s.name AS student_name,
            s.class_id,
            c.name AS class_name,
            c.grade_id,
            g.name AS grade_name,
            e.id AS exam_id,
            e.name AS exam_name,
            e.exam_type,
            e.exam_date,
            sub.id AS subject_id,
            sub.name AS subject_name,
            sub.is_core,
            sub.weight,
            sc.score,
            sc.rank_in_class,
            sc.rank_in_grade,
            sc.percentile,
            sc.is_makeup,
            sc.original_score,
            CASE WHEN sc.score >= ess.excellent_line THEN 1 ELSE 0 END AS is_excellent,
            CASE WHEN sc.score >= ess.good_line THEN 1 ELSE 0 END AS is_good,
            CASE WHEN sc.score >= ess.pass_line THEN 1 ELSE 0 END AS is_pass,
            CASE WHEN sc.score IS NULL OR sc.score < ess.low_line THEN 1 ELSE 0 END AS is_low
        FROM scores sc
        JOIN students s ON sc.student_id = s.id AND s.deleted_at IS NULL
        JOIN classes c ON s.class_id = c.id
        JOIN grades g ON c.grade_id = g.id
        JOIN exams e ON sc.exam_id = e.id
        JOIN subjects sub ON sc.subject_id = sub.id
        JOIN exam_subject_settings ess ON e.id = ess.exam_id AND sub.id = ess.subject_id
    """
        )
    )

    # ============================================================
    # 2. 年级学科统计视图
    # ============================================================
    conn.execute(sa.text("DROP VIEW IF EXISTS v_grade_subject_stats"))
    conn.execute(
        sa.text(
            """
        CREATE VIEW v_grade_subject_stats AS
        SELECT 
            e.id AS exam_id,
            g.id AS grade_id,
            sub.id AS subject_id,
            COUNT(sc.score) AS cnt,
            AVG(sc.score) AS avg_score,
            MAX(sc.score) AS max_score,
            MIN(sc.score) AS min_score,
            -- SQLite 中位数近似：排序后取中间值
            (SELECT AVG(score) FROM (
                SELECT sc2.score 
                FROM scores sc2
                JOIN students s2 ON sc2.student_id = s2.id AND s2.deleted_at IS NULL
                JOIN classes c2 ON s2.class_id = c2.id
                JOIN grades g2 ON c2.grade_id = g2.id
                JOIN exams e2 ON sc2.exam_id = e2.id
                JOIN subjects sub2 ON sc2.subject_id = sub2.id
                WHERE e2.id = e.id
                AND g2.id = g.id
                AND sub2.id = sub.id
                AND sc2.score IS NOT NULL
                ORDER BY sc2.score
                LIMIT 2 OFFSET (COUNT(sc.score) - 1) / 2
            )) AS median_score,
            SUM(CASE WHEN sc.score >= ess.excellent_line THEN 1 ELSE 0 END) * 100.0 / COUNT(sc.score) AS excellent_rate,
            SUM(CASE WHEN sc.score >= ess.good_line THEN 1 ELSE 0 END) * 100.0 / COUNT(sc.score) AS good_rate,
            SUM(CASE WHEN sc.score >= ess.pass_line THEN 1 ELSE 0 END) * 100.0 / COUNT(sc.score) AS pass_rate,
            SUM(CASE WHEN sc.score IS NULL OR sc.score < ess.low_line THEN 1 ELSE 0 END) * 100.0 / COUNT(sc.score) AS low_rate
        FROM scores sc
        JOIN exams e ON sc.exam_id = e.id
        JOIN students s ON sc.student_id = s.id AND s.deleted_at IS NULL
        JOIN classes c ON s.class_id = c.id
        JOIN grades g ON c.grade_id = g.id
        JOIN subjects sub ON sc.subject_id = sub.id
        JOIN exam_subject_settings ess ON e.id = ess.exam_id AND sub.id = ess.subject_id
        GROUP BY e.id, g.id, sub.id
    """
        )
    )

    # ============================================================
    # 3. 学生历史排名趋势视图
    # ============================================================
    conn.execute(sa.text("DROP VIEW IF EXISTS v_student_rank_trend"))
    conn.execute(
        sa.text(
            """
        CREATE VIEW v_student_rank_trend AS
        SELECT 
            s.id AS student_id,
            s.name AS student_name,
            s.class_id,
            c.name AS class_name,
            c.grade_id,
            e.id AS exam_id,
            e.name AS exam_name,
            e.exam_date,
            e.exam_type,
            sub.id AS subject_id,
            sub.name AS subject_name,
            sc.score,
            sc.rank_in_class,
            sc.rank_in_grade,
            sc.percentile,
            ROW_NUMBER() OVER (PARTITION BY s.id, sub.id ORDER BY e.exam_date) AS exam_seq
        FROM scores sc
        JOIN students s ON sc.student_id = s.id AND s.deleted_at IS NULL
        JOIN classes c ON s.class_id = c.id
        JOIN exams e ON sc.exam_id = e.id
        JOIN subjects sub ON sc.subject_id = sub.id
    """
        )
    )

    # ============================================================
    # 4. 定时刷新任务表（记录刷新历史）
    # ============================================================
    op.create_table(
        "dw_refresh_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("view_name", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, comment="running/success/failed"),
        sa.Column("rows_affected", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_dw_refresh_logs_view_time", "dw_refresh_logs", ["view_name", "started_at"])


def downgrade() -> None:
    conn = op.get_bind()
    for view in ["v_student_rank_trend", "v_grade_subject_stats", "v_fact_student_exam_score"]:
        conn.execute(sa.text(f"DROP VIEW IF EXISTS {view}"))

    op.drop_table("dw_refresh_logs")
