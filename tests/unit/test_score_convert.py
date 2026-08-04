"""
ScoreService.convert_scores 折算测试（Sprint 3.7.16）
覆盖：百分制折算、满分缩放、缺考跳过、幂等、自定义满分
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import Base, Exam, Score, Student, Subject
from edu_system.services.score import ScoreService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _exam(session):
    e = Exam(name="单元测试", grade_id=0, semester_id=0)
    session.add(e)
    session.commit()
    return e.id


def _mk(subject_name, full_mark, session, exam_id):
    s = Subject(name=subject_name, full_mark=full_mark)
    session.add(s)
    session.commit()
    return s.id


class TestConvertScores:
    def test_percent_convert(self, session):
        """120 分制 90 分折算为 75 分"""
        eid = _exam(session)
        sid = _mk("数学", 120, session, eid)
        st = Student(name="张三", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=90))
        session.commit()

        n = ScoreService(session).convert_scores(eid, full_marks={sid: 120})
        assert n == 1
        sc = session.query(Score).filter_by(exam_id=eid).first()
        assert sc.converted_score == 75.0

    def test_full_mark_100_no_change(self, session):
        """满分 100 时折算分 = 原始分"""
        eid = _exam(session)
        sid = _mk("语文", 100, session, eid)
        st = Student(name="李四", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=83.5))
        session.commit()

        ScoreService(session).convert_scores(eid, full_marks={sid: 100})
        sc = session.query(Score).filter_by(exam_id=eid).first()
        assert sc.converted_score == 83.5

    def test_absent_skipped(self, session):
        """缺考（score=None）不折算"""
        eid = _exam(session)
        sid = _mk("英语", 100, session, eid)
        st = Student(name="王五", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=None))
        session.commit()

        n = ScoreService(session).convert_scores(eid, full_marks={sid: 100})
        assert n == 0
        sc = session.query(Score).filter_by(exam_id=eid).first()
        assert sc.converted_score is None

    def test_idempotent(self, session):
        """重复折算覆盖且结果一致"""
        eid = _exam(session)
        sid = _mk("物理", 60, session, eid)
        st = Student(name="赵六", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=30))
        session.commit()

        svc = ScoreService(session)
        svc.convert_scores(eid, full_marks={sid: 60})
        sc1 = session.query(Score).filter_by(exam_id=eid).first().converted_score
        svc.convert_scores(eid, full_marks={sid: 60})
        sc2 = session.query(Score).filter_by(exam_id=eid).first().converted_score
        assert sc1 == sc2 == 50.0

    def test_default_full_marks_from_subject(self, session):
        """缺省 full_marks 用 Subject.full_mark"""
        eid = _exam(session)
        sid = _mk("化学", 200, session, eid)
        st = Student(name="钱七", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=100))
        session.commit()

        n = ScoreService(session).convert_scores(eid)
        assert n == 1
        sc = session.query(Score).filter_by(exam_id=eid).first()
        assert sc.converted_score == 50.0

    def test_custom_full_mark(self, session):
        """原始分满分灵活设置：满分 50 制，40 分 → 折算 80"""
        eid = _exam(session)
        sid = _mk("体育", 100, session, eid)
        st = Student(name="孙八", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=40))
        session.commit()

        ScoreService(session).convert_scores(eid, full_marks={sid: 50})
        sc = session.query(Score).filter_by(exam_id=eid).first()
        assert sc.converted_score == 80.0

    def test_custom_target_full_mark(self, session):
        """折算目标满分灵活设置：折算到 120 分制"""
        eid = _exam(session)
        sid = _mk("数学", 100, session, eid)
        st = Student(name="周九", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=80))
        session.commit()

        ScoreService(session).convert_scores(eid, full_marks={sid: 100}, target_full_mark=120)
        sc = session.query(Score).filter_by(exam_id=eid).first()
        assert sc.converted_score == 96.0

    def test_custom_both_marks(self, session):
        """满分与目标均自定义：50 制 30 分 → 折算到 150 制 = 90"""
        eid = _exam(session)
        sid = _mk("美术", 100, session, eid)
        st = Student(name="吴十", class_id=0, semester_id=0)
        session.add(st)
        session.commit()
        session.add(Score(exam_id=eid, student_id=st.id, subject_id=sid, score=30))
        session.commit()

        ScoreService(session).convert_scores(eid, full_marks={sid: 50}, target_full_mark=150)
        sc = session.query(Score).filter_by(exam_id=eid).first()
        assert sc.converted_score == 90.0
