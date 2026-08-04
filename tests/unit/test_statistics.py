"""
StatisticsService 单元测试 — 核心指标清单（M5-B1）

覆盖 30 个核心指标的计算正确性：
- 学生维度 5 个
- 班级维度 4 个
- 教师维度 2 个
- 成绩维度 5 个
- 考试维度 2 个
- 其他维度指标
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Class, Exam, Grade, Score, Semester, Student, Subject, Teacher
from edu_system.services.statistics import METRIC_KEYS, StatisticsService


@pytest.fixture
def session():
    """内存 SQLite 会话（含完整测试数据链）"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture(autouse=True)
def _clean_semester():
    """每个测试前清理线程局部学期，防止被测试数据集加载器/其他测试污染"""
    from edu_system.database import set_active_semester

    set_active_semester(0)
    yield
    set_active_semester(0)


@pytest.fixture
def test_data(session):
    """构造测试数据：学年/学期/年级/班级/学生/教师/学科/考试/成绩"""
    # 学年
    from edu_system.models import AcademicYear

    ay = AcademicYear(name="2024-2025", sort_order=0, is_active=True)
    session.add(ay)
    session.flush()

    # 学期（激活）
    sem = Semester(
        academic_year_id=ay.id,
        year_start=2024,
        semester="1",
        label="2024-2025 第1学期",
        sort_order=1,
        is_active=True,
        status="active",
    )
    session.add(sem)
    session.flush()

    # 设置全局激活学期（供 StatisticsService 读取）
    from edu_system.database import set_active_semester

    set_active_semester(sem.id)

    # 年级
    g1 = Grade(name="初一级", sort_order=1)
    g2 = Grade(name="初二级", sort_order=2)
    g3 = Grade(name="初三级", sort_order=3)
    session.add_all([g1, g2, g3])
    session.flush()

    # 班级
    c1 = Class(grade_id=g1.id, semester_id=sem.id, name="初一1班", class_type="普通班")
    c2 = Class(grade_id=g1.id, semester_id=sem.id, name="初一2班", class_type="普通班")
    c3 = Class(grade_id=g2.id, semester_id=sem.id, name="初二1班", class_type="实验班")
    c4 = Class(grade_id=g3.id, semester_id=sem.id, name="初三1班", class_type="普通班")
    session.add_all([c1, c2, c3, c4])
    session.flush()

    # 学科
    sub_chinese = Subject(
        name="语文", full_mark=120, pass_line=72, good_line=84, excellent_line=96, low_line=36
    )
    sub_math = Subject(
        name="数学", full_mark=120, pass_line=72, good_line=84, excellent_line=96, low_line=36
    )
    sub_english = Subject(
        name="英语", full_mark=120, pass_line=72, good_line=84, excellent_line=96, low_line=36
    )
    session.add_all([sub_chinese, sub_math, sub_english])
    session.flush()

    # 教师
    t1 = Teacher(name="张老师", title="高级教师", semester_id=sem.id)
    t2 = Teacher(name="李老师", title="一级教师", semester_id=sem.id)
    t3 = Teacher(name="王老师", title="二级教师", semester_id=sem.id)
    session.add_all([t1, t2, t3])
    session.flush()

    # 学生（分布在不同班级，不同性别/住宿）
    students = [
        # 初一1班：5人
        Student(
            class_id=c1.id,
            name="学生1",
            gender="男",
            boarding="住校",
            semester_id=sem.id,
            status="在校",
            student_code="S001",
        ),
        Student(
            class_id=c1.id,
            name="学生2",
            gender="女",
            boarding="走读",
            semester_id=sem.id,
            status="在校",
            student_code="S002",
        ),
        Student(
            class_id=c1.id,
            name="学生3",
            gender="男",
            boarding="住校",
            semester_id=sem.id,
            status="在校",
            student_code="S003",
        ),
        Student(
            class_id=c1.id,
            name="学生4",
            gender="女",
            boarding="走读",
            semester_id=sem.id,
            status="在校",
            student_code="S004",
        ),
        Student(
            class_id=c1.id,
            name="学生5",
            gender="男",
            boarding="住校",
            semester_id=sem.id,
            status="在校",
            student_code="S005",
        ),
        # 初一2班：3人
        Student(
            class_id=c2.id,
            name="学生6",
            gender="女",
            boarding="走读",
            semester_id=sem.id,
            status="在校",
            student_code="S006",
        ),
        Student(
            class_id=c2.id,
            name="学生7",
            gender="男",
            boarding="走读",
            semester_id=sem.id,
            status="在校",
            student_code="S007",
        ),
        Student(
            class_id=c2.id,
            name="学生8",
            gender="女",
            boarding="住校",
            semester_id=sem.id,
            status="在校",
            student_code="S008",
        ),
        # 初二1班：2人
        Student(
            class_id=c3.id,
            name="学生9",
            gender="男",
            boarding="住校",
            semester_id=sem.id,
            status="在校",
            student_code="S009",
        ),
        Student(
            class_id=c3.id,
            name="学生10",
            gender="女",
            boarding="走读",
            semester_id=sem.id,
            status="在校",
            student_code="S010",
        ),
        # 初三1班：0人（空班测试边界）
    ]
    session.add_all(students)
    session.flush()

    # 考试
    exam1 = Exam(semester_id=sem.id, name="期中考试", exam_type="midterm")
    exam2 = Exam(semester_id=sem.id, name="期末考试", exam_type="final")
    session.add_all([exam1, exam2])
    session.flush()

    # 成绩（为每个学生每科每考试生成分数）
    scores = []
    for stu in students:
        for sub in [sub_chinese, sub_math, sub_english]:
            # 期中
            scores.append(
                Score(
                    student_id=stu.id,
                    subject_id=sub.id,
                    exam_id=exam1.id,
                    score=80.0 if sub == sub_chinese else (85.0 if sub == sub_math else 75.0),
                )
            )
            # 期末
            scores.append(
                Score(
                    student_id=stu.id,
                    subject_id=sub.id,
                    exam_id=exam2.id,
                    score=90.0 if sub == sub_chinese else (95.0 if sub == sub_math else 85.0),
                )
            )
    session.add_all(scores)
    session.commit()

    return {
        "sem": sem,
        "grades": [g1, g2, g3],
        "classes": [c1, c2, c3, c4],
        "subjects": [sub_chinese, sub_math, sub_english],
        "teachers": [t1, t2, t3],
        "students": students,
        "exams": [exam1, exam2],
    }


class TestStudentMetrics:
    """学生维度指标测试（5 个核心指标）"""

    def test_student_count_school(self, session, test_data):
        """全校学生总数"""
        svc = StatisticsService(session)
        metrics = svc.compute_student_metrics("school", 0)
        assert metrics["student_count"] == 10.0

    def test_student_count_grade(self, session, test_data):
        """年级学生数"""
        svc = StatisticsService(session)
        g1 = test_data["grades"][0]
        metrics = svc.compute_student_metrics("grade", g1.id)
        assert metrics["student_count"] == 8.0  # 初一1班5 + 初一2班3

    def test_student_count_class(self, session, test_data):
        """班级学生数"""
        svc = StatisticsService(session)
        c1 = test_data["classes"][0]
        metrics = svc.compute_student_metrics("class", c1.id)
        assert metrics["student_count"] == 5.0

    def test_student_gender_split(self, session, test_data):
        """男/女生数"""
        svc = StatisticsService(session)
        metrics = svc.compute_student_metrics("school", 0)
        # 男: S1,S3,S5,S7,S9 = 5; 女: S2,S4,S6,S8,S10 = 5
        assert metrics["student_male"] == 5.0
        assert metrics["student_female"] == 5.0

    def test_student_boarding_split(self, session, test_data):
        """住校/走读生数"""
        svc = StatisticsService(session)
        metrics = svc.compute_student_metrics("school", 0)
        # 住校: S1,S3,S5,S8,S9 = 5; 走读: S2,S4,S6,S7,S10 = 5
        assert metrics["student_boarding"] == 5.0
        assert metrics["student_day"] == 5.0


class TestClassMetrics:
    """班级维度指标测试（4 个核心指标）"""

    def test_class_count_school(self, session, test_data):
        """全校班级数"""
        svc = StatisticsService(session)
        metrics = svc.compute_class_metrics("school", 0)
        assert metrics["class_count"] == 4.0

    def test_class_count_grade(self, session, test_data):
        """年级班级数"""
        svc = StatisticsService(session)
        g1 = test_data["grades"][0]
        metrics = svc.compute_class_metrics("grade", g1.id)
        assert metrics["class_count"] == 2.0

    def test_class_size_stats(self, session, test_data):
        """平均/最大/最小班额"""
        svc = StatisticsService(session)
        metrics = svc.compute_class_metrics("school", 0)
        # 班额: 5, 3, 2, 0
        assert metrics["class_avg_size"] == 2.5  # (5+3+2+0)/4
        assert metrics["class_max_size"] == 5.0
        assert metrics["class_min_size"] == 0.0

    def test_empty_class_min_size(self, session, test_data):
        """空班最小班额为 0"""
        svc = StatisticsService(session)
        c4 = test_data["classes"][3]  # 初三1班，0人
        metrics = svc.compute_class_metrics("class", c4.id)
        assert metrics["class_avg_size"] == 0.0
        assert metrics["class_max_size"] == 0.0
        assert metrics["class_min_size"] == 0.0


class TestTeacherMetrics:
    """教师维度指标测试（2 个核心指标）"""

    def test_teacher_count(self, session, test_data):
        """教师总数"""
        svc = StatisticsService(session)
        metrics = svc.compute_teacher_metrics("school", 0)
        assert metrics["teacher_count"] == 3.0

    def test_teacher_title_stats(self, session, test_data):
        """职称统计（简化：统计不同职称数）"""
        svc = StatisticsService(session)
        metrics = svc.compute_teacher_metrics("school", 0)
        # 高级教师、一级教师、二级教师 = 3 种
        assert metrics["teacher_title_stats"] == 3.0


class TestScoreMetrics:
    """成绩维度指标测试（5 个核心指标）"""

    def test_score_avg(self, session, test_data):
        """平均分"""
        svc = StatisticsService(session)
        metrics = svc.compute_score_metrics("school", 0)
        # 期中+期末，每人3科，每科分数：语文80/90, 数学85/95, 英语75/85
        # 总分 = 10人 * (80+85+75+90+95+85) = 10 * 510 = 5100
        # 总人次 = 10人 * 6科 = 60
        # 平均 = 5100/60 = 85
        assert metrics["score_avg"] == 85.0

    def test_score_pass_rate(self, session, test_data):
        """及格率（≥60）"""
        svc = StatisticsService(session)
        metrics = svc.compute_score_metrics("school", 0)
        # 所有分数都 ≥ 60，及格率 100%
        assert metrics["score_pass_rate"] == 100.0

    def test_score_good_rate(self, session, test_data):
        """良好率（≥80）"""
        svc = StatisticsService(session)
        metrics = svc.compute_score_metrics("school", 0)
        # 期中：语文80(良好), 数学85(良好), 英语75(不良好) → 2/3
        # 期末：语文90(良好), 数学95(良好), 英语85(良好) → 3/3
        # 总体：5/6 = 83.33%
        assert metrics["score_good_rate"] == 83.33

    def test_score_excellent_rate(self, session, test_data):
        """优秀率（≥90）"""
        svc = StatisticsService(session)
        metrics = svc.compute_score_metrics("school", 0)
        # 期中：无 ≥90
        # 期末：语文90, 数学95 → 2/3
        # 总体：2/6 = 33.33%
        assert metrics["score_excellent_rate"] == 33.33

    def test_score_distribution(self, session, test_data):
        """分段分布（返回实际有数据的分段数）"""
        svc = StatisticsService(session)
        metrics = svc.compute_score_metrics("school", 0)
        # 分段：<60, 60-69, 70-79, 80-89, 90+ = 5 个定义分段
        # 实际有数据的：70-79 (英语期中75), 80-89 (语文期中80, 数学期中85, 英语期末85), 90+ (语文期末90, 数学期末95) = 3 个
        assert metrics["score_distribution"] == 3.0


class TestExamMetrics:
    """考试维度指标测试（2 个核心指标）"""

    def test_exam_count(self, session, test_data):
        """考试场次"""
        svc = StatisticsService(session)
        metrics = svc.compute_exam_metrics()
        assert metrics["exam_count"] == 2.0

    def test_exam_participation(self, session, test_data):
        """平均参考率"""
        svc = StatisticsService(session)
        metrics = svc.compute_exam_metrics()
        # 所有学生都有所有科目的成绩 → 100%
        assert metrics["exam_participation"] == 100.0


class TestAllMetrics:
    """统一入口测试"""

    def test_compute_all_metrics_school(self, session, test_data):
        """全校所有指标"""
        svc = StatisticsService(session)
        metrics = svc.compute_all_metrics("school", 0)
        # 应包含所有 METRIC_KEYS 中的指标（至少核心的）
        assert "student_count" in metrics
        assert "class_count" in metrics
        assert "teacher_count" in metrics
        assert "score_avg" in metrics
        assert "exam_count" in metrics

    def test_metric_keys_coverage(self):
        """验证 METRIC_KEYS 覆盖指标数"""
        assert len(METRIC_KEYS) >= 21  # 当前实现的核心指标数


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
