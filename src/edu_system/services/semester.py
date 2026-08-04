"""
学期管理服务
"""

from sqlalchemy.orm import Session

from edu_system.models import Semester, SemesterStatus


class SemesterService:
    def __init__(self, session: Session):
        self.session = session

    def get_active(self) -> Semester | None:
        """获取当前激活学期"""
        return self.session.query(Semester).filter_by(is_active=True).first()

    def get_by_id(self, semester_id: int) -> Semester | None:
        return self.session.query(Semester).get(semester_id)

    def list_all(self) -> list[Semester]:
        return list(
            self.session.query(Semester)
            .order_by(Semester.year_start.desc(), Semester.sort_order)
            .all()
        )

    def set_active(self, semester_id: int) -> Semester | None:
        """设置激活学期"""
        self.session.query(Semester).update({"is_active": False})
        sem = self.get_by_id(semester_id)
        if sem:
            sem.is_active = True
            self.session.flush()
        return sem

    def create(
        self,
        academic_year_id: int,
        semester: str,
        label: str = None,
        sort_order: int = 0,
        start_date=None,
        end_date=None,
    ) -> Semester:
        """创建学期"""
        if not label:
            ay = self.session.query(AcademicYear).get(academic_year_id)
            if ay:
                label = f"{ay.name} 第{semester}学期"
            else:
                label = f"学期 {semester}"
        existing = (
            self.session.query(Semester)
            .filter_by(academic_year_id=academic_year_id, semester=semester)
            .first()
        )
        if existing:
            return existing
        sem = Semester(
            academic_year_id=academic_year_id,
            year_start=academic_year_id,  # 临时用 academic_year_id 作为 year_start
            semester=semester,
            label=label or f"学期 {semester}",
            sort_order=sort_order,
            is_active=False,
            status=SemesterStatus.draft,
            start_date=start_date,
            end_date=end_date,
        )
        self.session.add(sem)
        self.session.flush()
        return sem

    def ensure_semesters(self, academic_year_id: int, active_semester: str = "1") -> Semester:
        """确保学年下的学期存在，并设置激活学期"""
        from edu_system.models import AcademicYear

        ay = self.session.query(AcademicYear).get(academic_year_id)
        if not ay:
            ay = AcademicYear(name=f"{academic_year_id}-{academic_year_id + 1}", is_active=True)
            self.session.add(ay)
            self.session.flush()
            academic_year_id = ay.id

        for sem_name in ["1", "2"]:
            self.create(academic_year_id, sem_name, sort_order=1 if sem_name == "1" else 2)

        current = (
            self.session.query(Semester)
            .filter_by(academic_year_id=academic_year_id, semester=active_semester)
            .first()
        )
        if current:
            self.set_active(current.id)
        return current

    def activate(self, semester_id: int) -> Semester | None:
        """激活学期（设置为 active 状态）"""
        sem = self.set_active(semester_id)
        if sem:
            sem.status = SemesterStatus.active
            self.session.flush()
        return sem

    def lock(self, semester_id: int) -> Semester | None:
        """锁定学期（仅查询/导出）"""
        sem = self.get_by_id(semester_id)
        if sem:
            sem.status = SemesterStatus.locked
            sem.is_active = False
            self.session.flush()
        return sem

    def archive(self, semester_id: int) -> Semester | None:
        """归档学期（只读）"""
        sem = self.get_by_id(semester_id)
        if sem:
            sem.status = SemesterStatus.archived
            sem.is_active = False
            self.session.flush()
        return sem
