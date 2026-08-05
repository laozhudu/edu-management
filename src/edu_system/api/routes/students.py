"""
学生 API 路由（M5-E3 学生查分）

- GET /students/me/scores: 仅本人成绩（当前登录用户关联的学生）
  - 返回: 成绩列表 + 各科趋势（按考试日期排序）+ 汇总
  - 缓存: 内存 TTL 缓存（30s），避免重复查询
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import Exam, Score, Student, User

router = APIRouter(prefix="/students", tags=["学生"])

# 简单内存缓存: {key: (expire_at, data)}
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 30  # 秒


class ScoreItem(BaseModel):
    exam_id: int
    exam_name: str
    exam_date: str | None
    subject_id: int
    subject_name: str
    score: float | None
    converted_score: float | None
    is_makeup: bool
    is_published: bool


class TrendPoint(BaseModel):
    exam_id: int
    exam_name: str
    exam_date: str | None
    score: float | None


class SubjectTrend(BaseModel):
    subject_id: int
    subject_name: str
    points: list[TrendPoint]


class MyScoresResponse(BaseModel):
    student_id: int
    student_name: str
    student_no: str
    scores: list[ScoreItem]
    trends: list[SubjectTrend]
    total: int
    published_only: int


def _student_of_user(db: Session, user: User) -> Student | None:
    """当前用户关联的学生（按姓名/学号匹配，或 user.student_id 扩展）"""
    student_id = getattr(user, "student_id", None)
    if student_id:
        return db.query(Student).get(student_id)
    # 兜底：按姓名匹配（用户名=学生姓名场景）
    return db.query(Student).filter(Student.name == user.username).first()


@router.get("/me/scores", response_model=MyScoresResponse)
def my_scores(
    published_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """仅本人成绩查询（M5-E3）

    当前用户必须是学生（或关联学生），返回其全部成绩 +
    各科按考试时间排序的趋势点。
    """
    cache_key = f"me_scores:{current_user.id}:{published_only}"
    now = time.time()
    hit = _cache.get(cache_key)
    if hit and hit[0] > now:
        return hit[1]

    student = _student_of_user(db, current_user)
    if not student:
        raise HTTPException(status_code=404, detail="当前用户未关联学生档案")

    query = db.query(Score).filter(Score.student_id == student.id)
    if published_only:
        query = query.filter(Score.is_published == True)  # noqa: E712
    scores = query.order_by(Score.exam_id, Score.subject_id).all()

    # 按科目聚合趋势（按考试日期排序）
    exam_cache: dict[int, Exam] = {}
    trends_map: dict[int, SubjectTrend] = {}

    def _exam(eid: int) -> Exam | None:
        if eid not in exam_cache:
            exam_cache[eid] = db.query(Exam).get(eid)
        return exam_cache[eid]

    items = []
    for s in scores:
        exam = _exam(s.exam_id)
        items.append(
            ScoreItem(
                exam_id=s.exam_id,
                exam_name=exam.name if exam else f"考试{s.exam_id}",
                exam_date=exam.exam_date.isoformat() if exam and exam.exam_date else None,
                subject_id=s.subject_id,
                subject_name=s.subject.name if s.subject else f"科目{s.subject_id}",
                score=s.score,
                converted_score=s.converted_score,
                is_makeup=s.is_makeup,
                is_published=s.is_published,
            )
        )
        st = trends_map.get(s.subject_id)
        if st is None:
            st = SubjectTrend(
                subject_id=s.subject_id,
                subject_name=s.subject.name if s.subject else f"科目{s.subject_id}",
                points=[],
            )
            trends_map[s.subject_id] = st
        st.points.append(
            TrendPoint(
                exam_id=s.exam_id,
                exam_name=exam.name if exam else f"考试{s.exam_id}",
                exam_date=exam.exam_date.isoformat() if exam and exam.exam_date else None,
                score=s.score,
            )
        )

    data = MyScoresResponse(
        student_id=student.id,
        student_name=student.name,
        student_no=student.student_no or "",
        scores=items,
        trends=list(trends_map.values()),
        total=len(items),
        published_only=sum(1 for i in items if i.is_published),
    ).model_dump()

    _cache[cache_key] = (now + _CACHE_TTL, data)
    return data


def clear_score_cache() -> None:
    """清空缓存（测试/数据变更时调用）"""
    _cache.clear()
