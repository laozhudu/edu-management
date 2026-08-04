"""
学生业务服务 — 所有学生操作的核心编排层
使用 Result[T] 统一返回，使用 PageRequest/PageResponse 标准化分页查询
"""

from typing import Optional

from sqlalchemy import case as sa_case
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from edu_system.core.result import ErrorCodes, Result
from edu_system.models import Class as ClassModel
from edu_system.models import Grade, Student
from edu_system.repository.base import BaseRepository
from edu_system.schemas import (
    PageResponse,
    StudentCreateDTO,
    StudentFilter,
    StudentPageRequest,
    StudentUpdateDTO,
)


class StudentRepository(BaseRepository[Student]):
    def __init__(self, session: Session):
        super().__init__(session, Student)

    # ── 查询 ──

    def search(self, filter_: StudentFilter) -> Result[list[Student]]:
        """多条件筛选学生（兼容旧接口）"""
        try:
            q = self.session.query(Student).join(Student.class_)

            if filter_.grade:
                grade_prefix = {"初一级": "1", "初二级": "2", "初三级": "3"}.get(filter_.grade, "")
                if grade_prefix:
                    q = q.filter(ClassModel.name.like(f"{grade_prefix}%"))

            if filter_.class_name:
                q = q.filter(ClassModel.name == filter_.class_name)

            if filter_.status:
                q = q.filter(Student.status == filter_.status)

            if filter_.keyword:
                kw = f"%{filter_.keyword}%"
                q = q.filter(or_(Student.name.like(kw), Student.student_no.like(kw)))

            return Result.success(q.order_by(ClassModel.name, Student.student_no).all())
        except Exception as e:
            return Result.fail(f"查询失败: {e}", ErrorCodes.DATABASE_ERROR)

    def search_paginated(self, request: StudentPageRequest) -> Result[PageResponse[Student]]:
        """标准化分页查询"""
        try:
            generic = request.to_generic()
            q = self.session.query(Student).join(Student.class_)

            # 应用过滤器
            for f in generic.filters:
                if f.operator == "eq":
                    q = q.filter(getattr(Student, f.field) == f.value)
                elif f.operator == "like":
                    q = q.filter(getattr(Student, f.field).like(f.value))
                elif f.operator == "gte":
                    q = q.filter(getattr(Student, f.field) >= f.value)
                elif f.operator == "lte":
                    q = q.filter(getattr(Student, f.field) <= f.value)

            # 班级名过滤（通过 join）
            for f in generic.filters:
                if f.field == "class_name":
                    if f.operator == "eq":
                        q = q.filter(ClassModel.name == f.value)
                    elif f.operator == "like":
                        q = q.filter(ClassModel.name.like(f.value))

            total = q.count()

            # 排序
            for s in generic.sort:
                col = getattr(Student, s.field, None) or getattr(ClassModel, s.field, None)
                if col is not None:
                    q = q.order_by(col.desc() if s.desc else col.asc())
            if not generic.sort:
                q = q.order_by(ClassModel.name, Student.student_no)

            items = q.offset(generic.offset).limit(generic.limit).all()
            return Result.success(PageResponse.create(items, total, generic))
        except Exception as e:
            return Result.fail(f"分页查询失败: {e}", ErrorCodes.DATABASE_ERROR)

    def count(self, filter_: StudentFilter) -> Result[int]:
        """仅查总数，用于启动时快速获取总数"""
        try:
            q = self.session.query(Student).join(Student.class_)

            if filter_.grade:
                grade_prefix = {"初一级": "1", "初二级": "2", "初三级": "3"}.get(filter_.grade, "")
                if grade_prefix:
                    q = q.filter(ClassModel.name.like(f"{grade_prefix}%"))

            if filter_.class_name:
                q = q.filter(ClassModel.name == filter_.class_name)

            if filter_.status:
                q = q.filter(Student.status == filter_.status)

            if filter_.keyword:
                kw = f"%{filter_.keyword}%"
                q = q.filter(or_(Student.name.like(kw), Student.student_no.like(kw)))

            return Result.success(q.count())
        except Exception as e:
            return Result.fail(f"统计失败: {e}", ErrorCodes.DATABASE_ERROR)

    def list_by_class(self, class_id: int) -> Result[list[Student]]:
        try:
            return Result.success(
                self.session.query(Student)
                .filter(Student.class_id == class_id)
                .order_by(Student.student_no)
                .all()
            )
        except Exception as e:
            return Result.fail(f"查询失败: {e}", ErrorCodes.DATABASE_ERROR)

    def delete(self, student_id: int) -> Result[bool]:
        """删除学生（不提交事务，由调用方控制）"""
        try:
            student = self.session.query(Student).get(student_id)
            if student:
                self.session.delete(student)
                self.session.flush()
                return Result.success(True)
            return Result.fail("学生不存在", ErrorCodes.STUDENT_NOT_FOUND)
        except Exception as e:
            return Result.fail(f"删除失败: {e}", ErrorCodes.DATABASE_ERROR)

    def count_by_grade(self) -> Result[list[dict]]:
        """各年级学生数统计"""
        try:
            rows = (
                self.session.query(
                    Grade.name,
                    func.count(Student.id).label("count"),
                    func.sum(sa_case((Student.gender == "男", 1), else_=0)).label("male"),
                )
                .select_from(Student)
                .join(Student.class_)
                .join(ClassModel.grade)
                .filter(Student.status == "在校")
                .group_by(Grade.name)
                .order_by(Grade.sort_order)
                .all()
            )
            return Result.success([{"grade": r[0], "total": r[1], "male": r[2] or 0} for r in rows])
        except Exception as e:
            return Result.fail(f"统计失败: {e}", ErrorCodes.DATABASE_ERROR)

    # ── 写入 ──

    def create_from_dto(self, data: "StudentCreateDTO") -> Result["Student"]:
        """用校验后的数据创建学生"""
        try:
            cls = self.session.query(ClassModel).filter_by(name=data.class_name).first()
            if not cls:
                grade_prefix = data.class_name[0]
                grade_map = {"1": "初一级", "2": "初二级", "3": "初三级"}
                grade_name = grade_map.get(grade_prefix, "初一级")
                grade = self.session.query(Grade).filter_by(name=grade_name).first()
                if not grade:
                    return Result.fail(f"未找到年级: {grade_name}", ErrorCodes.CLASS_NOT_FOUND)
                cls = ClassModel(grade_id=grade.id, name=data.class_name)
                self.session.add(cls)
                self.session.flush()

            student = Student(
                class_id=cls.id,
                name=data.name,
                student_no=data.student_no,
                gender=data.gender,
                id_card=data.id_card,
                phone=data.phone,
                ethnicity=data.ethnicity,
                address=data.address,
                enroll_year=data.enroll_year,
                boarding=data.boarding,
                status=data.status,
                note=data.note,
            )
            self.session.add(student)
            self.session.flush()
            return Result.success(student)
        except Exception as e:
            return Result.fail(f"创建失败: {e}", ErrorCodes.DATABASE_ERROR)

    def update_from_dto(
        self, student_id: int, data: "StudentUpdateDTO"
    ) -> Result[Optional["Student"]]:
        """部分更新学生"""
        try:
            student = self.get(student_id)
            if not student:
                return Result.fail("学生不存在", ErrorCodes.STUDENT_NOT_FOUND)

            update_data = data.model_dump(exclude_none=True)
            for key, value in update_data.items():
                if hasattr(student, key):
                    setattr(student, key, value)

            self.session.flush()
            return Result.success(student)
        except Exception as e:
            return Result.fail(f"更新失败: {e}", ErrorCodes.DATABASE_ERROR)

    def graduate_class(self, class_id: int) -> Result[int]:
        """班级批量毕业"""
        try:
            count = (
                self.session.query(Student)
                .filter(Student.class_id == class_id, Student.status == "在校")
                .update({"status": "毕业"})
            )
            self.session.flush()
            return Result.success(count)
        except Exception as e:
            return Result.fail(f"毕业操作失败: {e}", ErrorCodes.DATABASE_ERROR)

    def batch_transfer(self, student_ids: list[int], target_class_id: int) -> Result[int]:
        """批量转班"""
        try:
            count = (
                self.session.query(Student)
                .filter(Student.id.in_(student_ids))
                .update({"class_id": target_class_id}, synchronize_session=False)
            )
            self.session.flush()
            return Result.success(count)
        except Exception as e:
            return Result.fail(f"批量转班失败: {e}", ErrorCodes.DATABASE_ERROR)
