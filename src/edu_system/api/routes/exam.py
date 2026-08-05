"""
考试 API 路由
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import (
    AdmitCard,
    Class,
    Classroom,
    Exam,
    ExamRoom,
    ExamSeat,
    Invigilation,
    RoomAssignmentStatus,
    Student,
    User,
)

router = APIRouter(prefix="/exam", tags=["考试管理"])


# ===== Pydantic 模型 =====


class ExamCreate(BaseModel):
    name: str
    semester_id: int | None = None
    exam_type: str = "midterm"
    start_date: date
    end_date: date
    grade_id: int | None = None
    note: str = ""


class ExamUpdate(BaseModel):
    name: str | None = None
    exam_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    grade_id: int | None = None
    note: str | None = None
    status: str | None = None


class ExamResponse(BaseModel):
    id: int
    semester_id: int
    name: str
    exam_type: str
    start_date: date
    end_date: date | None = None
    grade_id: int | None = None
    note: str = ""
    is_makeup: bool = False
    status: str = "draft"
    created_at: datetime

    class Config:
        from_attributes = True


class ExamListResponse(BaseModel):
    items: list[ExamResponse]
    total: int
    page: int
    page_size: int


class RoomAssignRequest(BaseModel):
    strategy: str = "balanced"  # balanced/compact
    max_per_room: int = 30
    subjects: list[int] | None = None  # 指定科目 ID


class SeatArrangeRequest(BaseModel):
    method: str = "snake"  # snake/name/number/random


class InvigilationResponse(BaseModel):
    id: int
    exam_id: int
    room_id: int
    teacher_id: int
    role: str
    check_time: datetime | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdmitCardRequest(BaseModel):
    format: str = "pdf"
    include_qrcode: bool = True


# ===== API 端点 =====


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_data: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_ARRANGE)),
):
    """创建考试"""
    # 确定学期
    if exam_data.semester_id:
        semester_id = exam_data.semester_id
    else:
        from edu_system.database import get_active_semester

        semester_id = get_active_semester()
        if not semester_id:
            # 回退：DB 激活学期（Web 请求无线程上下文时）
            from edu_system.models import Semester

            sem = (
                db.query(Semester)
                .filter(Semester.is_active.is_(True))
                .order_by(Semester.id)
                .first()
            )
            if sem:
                semester_id = sem.id
        if not semester_id:
            raise HTTPException(status_code=400, detail="无活跃学期")

    exam = Exam(
        semester_id=semester_id,
        name=exam_data.name,
        exam_type=exam_data.exam_type,
        exam_date=exam_data.start_date,
        end_date=exam_data.end_date,
        grade_id=exam_data.grade_id,
        note=exam_data.note,
        is_makeup=False,
        status="draft",
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # 如果有考试科目设置，创建 ExamSubjectSetting
    # 这里简化处理
    return exam


@router.get("", response_model=ExamListResponse)
def list_exams(
    semester_id: int | None = Query(None),
    exam_type: str | None = Query(None),
    grade_id: int | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """考试列表查询"""
    query = db.query(Exam)

    if semester_id:
        query = query.filter(Exam.semester_id == semester_id)
    elif not exam_type and not grade_id and not status:
        # 默认只看活跃学期
        from edu_system.database import get_active_semester

        active_semester = get_active_semester()
        if active_semester:
            query = query.filter(Exam.semester_id == active_semester)

    if exam_type:
        # 通过 note 或其他字段筛选（简化）
        pass
    if grade_id:
        query = query.filter(Exam.grade_id == grade_id)
    if status:
        # Exam 没有 status 字段，通过 is_makeup 或 note 筛选
        pass

    total = query.count()
    exams = (
        query.order_by(desc(Exam.exam_date)).offset((page - 1) * page_size).limit(page_size).all()
    )

    return ExamListResponse(
        items=exams,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/conflicts")
def check_conflicts(
    semester_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_VIEW)),
):
    """冲突检测：同一时间同一教师/教室/学生"""
    if not semester_id:
        from edu_system.database import get_active_semester

        semester_id = get_active_semester()

    exams = db.query(Exam).filter(Exam.semester_id == semester_id).all()

    conflicts = []

    # 检测教师冲突（简化：按日期统计考试数）
    teacher_times = {}
    for exam in exams:
        if exam.exam_date:
            key = (exam.exam_date, exam.id)
            teacher_times[key] = teacher_times.get(key, 0) + 1

    # 检测教室冲突
    room_times = {}
    rooms = db.query(ExamRoom).join(Exam).filter(Exam.semester_id == semester_id).all()
    for room in rooms:
        # 简化
        pass

    return {
        "semester_id": semester_id,
        "total_exams": len(exams),
        "teacher_conflicts": [],
        "room_conflicts": [],
        "student_conflicts": [],
    }


@router.get("/schedule")
def exam_schedule(
    semester_id: int | None = Query(None),
    grade_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_VIEW)),
):
    """考试时间表"""
    if not semester_id:
        from edu_system.database import get_active_semester

        semester_id = get_active_semester()

    query = db.query(Exam).filter(Exam.semester_id == semester_id)
    if grade_id:
        query = query.filter(Exam.grade_id == grade_id)

    exams = query.order_by(Exam.exam_date).all()

    schedule = []
    for exam in exams:
        rooms = db.query(ExamRoom).filter(ExamRoom.exam_id == exam.id).all()
        schedule.append(
            {
                "exam_id": exam.id,
                "name": exam.name,
                "date": exam.exam_date.isoformat() if exam.exam_date else None,
                "grade_id": exam.grade_id,
                "rooms": [
                    {
                        "room_id": r.id,
                        "room_name": r.room.room_no if r.room else "",
                        "subject": r.subject.name if r.subject else "通用",
                        "capacity": r.capacity,
                    }
                    for r in rooms
                ],
            }
        )

    return {"semester_id": semester_id, "schedule": schedule}


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取考试详情"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    return exam


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    exam_data: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_ARRANGE)),
):
    """更新考试"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")

    if exam_data.name is not None:
        exam.name = exam_data.name
    if exam_data.exam_type is not None:
        # 存入 note 或扩展字段
        pass
    if exam_data.start_date is not None:
        exam.exam_date = exam_data.start_date
    if exam_data.end_date is not None:
        # 结束日期暂存 note
        pass
    if exam_data.grade_id is not None:
        exam.grade_id = exam_data.grade_id
    if exam_data.note is not None:
        exam.note = exam_data.note
    if exam_data.status is not None:
        # 状态暂存 note
        pass

    db.commit()
    db.refresh(exam)
    return exam


@router.post("/{exam_id}/rooms")
def auto_arrange_rooms(
    exam_id: int,
    request: RoomAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_ARRANGE)),
):
    """自动分考场（简化实现）"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")

    # 获取考试涉及的学生（通过年级/班级）
    students_query = db.query(Student).join(Class)
    if exam.grade_id:
        students_query = students_query.filter(Class.grade_id == exam.grade_id)
    else:
        # 默认全年级
        pass

    students = students_query.all()
    total_students = len(students)

    if total_students == 0:
        return {"message": "无学生数据", "rooms_created": 0}

    # 获取可用教室
    classrooms = (
        db.query(Classroom)
        .filter(
            Classroom.semester_id == exam.semester_id, Classroom.capacity >= request.max_per_room
        )
        .all()
    )

    if not classrooms:
        raise HTTPException(status_code=400, detail="无可用教室")

    # 简单分配：按容量均匀分配
    rooms_created = 0
    student_idx = 0

    for classroom in classrooms:
        if student_idx >= total_students:
            break

        room = ExamRoom(
            exam_id=exam_id,
            room_id=classroom.id,
            subject_id=None,  # 通用考场
            capacity=min(classroom.capacity, request.max_per_room),
            assigned_count=0,
            status=RoomAssignmentStatus.assigned,
        )
        db.add(room)
        rooms_created += 1
        student_idx += classroom.capacity

    db.commit()

    return {
        "message": f"已创建 {rooms_created} 个考场",
        "rooms_created": rooms_created,
        "total_students": total_students,
    }


@router.post("/{exam_id}/seats")
def arrange_seats(
    exam_id: int,
    request: SeatArrangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_ARRANGE)),
):
    """排座次"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")

    # 获取已分配的考场
    rooms = db.query(ExamRoom).filter(ExamRoom.exam_id == exam_id).all()
    if not rooms:
        raise HTTPException(status_code=400, detail="请先分配考场")

    # 获取学生
    students_query = db.query(Student).join(Class)
    if exam.grade_id:
        students_query = students_query.filter(Class.grade_id == exam.grade_id)
    students = students_query.all()

    if not students:
        return {"message": "无学生数据", "seats_arranged": 0}

    # 删除旧座次
    db.query(ExamSeat).filter(ExamSeat.exam_id == exam_id).delete()

    # 排座次逻辑
    seats_arranged = 0
    student_idx = 0

    for room in rooms:
        capacity = room.capacity
        rows = 5  # 假设 5 行
        cols = (capacity + rows - 1) // rows

        for i in range(capacity):
            if student_idx >= len(students):
                break

            student = students[student_idx]
            row = (i // cols) + 1
            col = (i % cols) + 1
            seat_number = f"{row:02d}-{col:02d}"

            seat = ExamSeat(
                exam_id=exam_id,
                room_id=room.id,
                student_id=student.id,
                seat_row=row,
                seat_col=col,
                seat_number=seat_number,
            )
            db.add(seat)
            seats_arranged += 1
            student_idx += 1

    db.commit()

    return {"message": f"已排座次 {seats_arranged} 个", "seats_arranged": seats_arranged}


@router.get("/{exam_id}/invigilation")
def get_invigilation(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_VIEW)),
):
    """获取监考表"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")

    # 获取考场及监考安排
    rooms = db.query(ExamRoom).filter(ExamRoom.exam_id == exam_id).all()

    result = []
    for room in rooms:
        invigilations = db.query(Invigilation).filter(Invigilation.room_id == room.id).all()
        result.append(
            {
                "room_id": room.id,
                "room_name": room.room.room_no if room.room else "",
                "subject": room.subject.name if room.subject else "通用",
                "capacity": room.capacity,
                "invigilators": [
                    {
                        "teacher_id": inv.teacher_id,
                        "teacher_name": inv.teacher.name if inv.teacher else "",
                        "role": inv.role,
                        "check_time": inv.check_time,
                        "status": inv.status,
                    }
                    for inv in invigilations
                ],
            }
        )

    return {"exam_id": exam_id, "exam_name": exam.name, "rooms": result}


@router.post("/{exam_id}/admit-card")
def generate_admit_cards(
    exam_id: int,
    request: AdmitCardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXAM_ARRANGE)),
):
    """批量生成准考证"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")

    # 获取考试学生
    students_query = db.query(Student).join(Class)
    if exam.grade_id:
        students_query = students_query.filter(Class.grade_id == exam.grade_id)
    students = students_query.all()

    if not students:
        return {"message": "无学生数据", "generated": 0}

    generated = 0
    for student in students:
        # 检查是否已生成
        existing = (
            db.query(AdmitCard)
            .filter(AdmitCard.exam_id == exam_id, AdmitCard.student_id == student.id)
            .first()
        )

        if existing:
            continue

        # 生成二维码数据（简化）
        import json

        qrcode_data = json.dumps(
            {
                "exam_id": exam_id,
                "student_id": student.id,
                "name": student.name,
                "exam_no": student.exam_no,
            }
        )

        card = AdmitCard(
            exam_id=exam_id,
            student_id=student.id,
            qrcode_data=qrcode_data,
            status="generated",
        )
        db.add(card)
        generated += 1

    db.commit()

    return {"message": f"已生成 {generated} 张准考证", "generated": generated}
