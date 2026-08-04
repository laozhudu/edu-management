"""
学生内存仓库 — 基于 MemoryCache 的零 SQL 查询实现
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from edu_system.cache import get_cache
from edu_system.core.result import ErrorCodes, Result
from edu_system.models import Student
from edu_system.schemas import PageResponse, StudentPageRequest


@dataclass
class CachedStudentFilter:
    """兼容旧接口的筛选器"""

    grade: str = ""
    class_name: str = ""
    status: str = ""
    keyword: str = ""


class MemoryStudentRepository:
    """内存模式学生仓库：零 SQL，全内存筛选/排序/分页"""

    def __init__(self, session: Session = None):
        self.session = session
        self.cache = get_cache()
        # 确保缓存已加载
        if not self.cache.students:
            if session:
                self.cache.load_all(session)
            else:
                raise RuntimeError("Cache not loaded and no session provided")

    def ensure_loaded(self, session: Session):
        """确保缓存已加载（用于首次初始化）"""
        if not self.cache.students:
            self.cache.load_all(session)

    # ── 兼容旧接口 ──

    def search(self, filter_: CachedStudentFilter) -> Result[list]:
        """多条件筛选学生（内存模式）"""
        try:
            students = self.cache.filter_students(
                grade_id=None,  # 通过 grade 参数转换
                class_name=filter_.class_name if filter_.class_name != "全部" else None,
                status=filter_.status if filter_.status != "全部" else None,
                keyword=filter_.keyword,
            )
            # 年级筛选
            if filter_.grade and filter_.grade != "全部":
                grade_prefix = {"初一级": "1", "初二级": "2", "初三级": "3"}.get(filter_.grade, "")
                students = [
                    s for s in students if s.class_name and s.class_name.startswith(grade_prefix)
                ]

            # 排序
            students.sort(
                key=lambda s: (s.class_name or "", int(s.student_no or 0) if s.student_no else 0)
            )
            return Result.success(students)
        except Exception as e:
            return Result.fail(f"查询失败: {e}", ErrorCodes.DATABASE_ERROR)

    def search_paginated(self, request: StudentPageRequest) -> Result[PageResponse]:
        """标准化分页查询（内存模式）"""
        try:
            # 转换过滤器
            filters = request.to_generic().filters
            grade = class_name = status = keyword = None
            for f in request.to_generic().filters:
                if f.field == "grade":
                    grade = f.value
                elif f.field == "class_name":
                    class_name = f.value
                elif f.field == "status":
                    status = f.value
                elif f.field in ("name", "student_code", "id_card", "phone"):
                    keyword = f.value

            students = self.cache.filter_students(
                class_name=class_name if class_name != "全部" else None,
                status=status if status != "全部" else None,
                keyword=keyword,
            )

            if grade:
                grade_prefix = {"初一级": "1", "初二级": "2", "初三级": "3"}.get(grade, "")
                students = [
                    s for s in students if s.class_name and s.class_name.startswith(grade_prefix)
                ]

            # 排序
            for s in request.to_generic().sort:
                if s.field == "class_name":
                    students.sort(key=lambda x: x.class_name or "", reverse=s.desc)
                elif s.field == "student_no":
                    students.sort(key=lambda x: int(x.student_no or 0), reverse=s.desc)
                elif s.field == "name":
                    students.sort(key=lambda x: x.name or "", reverse=s.desc)

            if not students or not request.to_generic().sort:
                students.sort(
                    key=lambda x: (
                        x.class_name or "",
                        int(x.student_no or 0) if x.student_no else 0,
                    )
                )

            total = len(students)
            generic = request.to_generic()
            items = students[generic.offset : generic.offset + generic.limit]
            return Result.success(PageResponse.create(items, total, generic))
        except Exception as e:
            return Result.fail(f"分页查询失败: {e}", ErrorCodes.DATABASE_ERROR)

    def count(self, filter_: CachedStudentFilter) -> Result[int]:
        """仅查总数（内存模式）"""
        try:
            students = self.cache.filter_students(
                class_name=filter_.class_name if filter_.class_name != "全部" else None,
                status=filter_.status if filter_.status != "全部" else None,
                keyword=filter_.keyword,
            )
            if filter_.grade and filter_.grade != "全部":
                grade_prefix = {"初一级": "1", "初二级": "2", "初三级": "3"}.get(filter_.grade, "")
                students = [
                    s for s in students if s.class_name and s.class_name.startswith(grade_prefix)
                ]
            return Result.success(len(students))
        except Exception as e:
            return Result.fail(f"统计失败: {e}", ErrorCodes.DATABASE_ERROR)

    def list_by_class(self, class_id: int) -> Result[list]:
        """按班级查询（内存模式）"""
        try:
            cls = self.cache.get_class(class_id)
            if not cls:
                return Result.success([])
            students = self.cache.get_students_by_class(class_id)
            students.sort(key=lambda s: int(s.student_no or 0) if s.student_no else 0)
            return Result.success(students)
        except Exception as e:
            return Result.fail(f"查询失败: {e}", ErrorCodes.DATABASE_ERROR)

    def count_by_grade(self) -> Result[list[dict]]:
        """各年级学生数统计（内存模式）"""
        try:
            result = []
            for g in self.cache.grades.values():
                students = self.cache.get_students_by_grade(g.id)
                total = len(students)
                male = sum(1 for s in students if s.gender == "男")
                result.append({"grade": g.name, "total": total, "male": male})
            return Result.success(result)
        except Exception as e:
            return Result.fail(f"统计失败: {e}", ErrorCodes.DATABASE_ERROR)

    # ── 写入操作（仍需 DB，但同步更新缓存）──

    def create_from_dto(self, data: "StudentCreateDTO") -> Result["Student"]:
        """创建学生（写 DB + 更新缓存）"""
        try:
            from edu_system.models import Student

            cls = self.cache.get_class_by_name(data.class_name)
            if not cls:
                grade = self.cache.get_grade_by_name(data.class_name[0])
                if not grade:
                    return Result.fail("未找到年级", ErrorCodes.CLASS_NOT_FOUND)
                from edu_system.models import Class

                cls = Class(grade_id=grade.id, name=data.class_name)
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

            # 同步缓存
            self.cache.students[student.id] = student
            self.cache.students_by_class[cls.id].append(student)
            self.cache.students_by_grade[cls.grade_id].append(student)
            self.cache.students_in_school.append(student)

            return Result.success(student)
        except Exception as e:
            return Result.fail(f"创建失败: {e}", ErrorCodes.DATABASE_ERROR)

    def update_from_dto(
        self, student_id: int, data: "StudentUpdateDTO"
    ) -> Result[Optional["Student"]]:
        """部分更新学生（写 DB + 更新缓存）"""
        try:
            student = self.cache.get_student(student_id)
            if not student:
                return Result.fail("学生不存在", ErrorCodes.STUDENT_NOT_FOUND)

            old_class_id = student.class_id
            update_data = data.model_dump(exclude_none=True)
            for key, value in update_data.items():
                if hasattr(student, key):
                    setattr(student, key, value)

            self.session.flush()

            # 同步缓存（如果班级变了，需要移动索引）
            if "class_id" in update_data and update_data["class_id"] != old_class_id:
                new_cls_id = update_data["class_id"]
                # 从旧班级移除
                if old_class_id in self.cache.students_by_class:
                    self.cache.students_by_class[old_class_id] = [
                        s for s in self.cache.students_by_class[old_class_id] if s.id != student_id
                    ]
                # 添加到新班级
                self.cache.students_by_class[new_cls_id].append(student)
                # 年级索引也要更新
                old_cls = self.cache.get_class(old_class_id)
                new_cls = self.cache.get_class(new_cls_id)
                if old_cls and old_cls.grade_id in self.cache.students_by_grade:
                    self.cache.students_by_grade[old_cls.grade_id] = [
                        s
                        for s in self.cache.students_by_grade[old_cls.grade_id]
                        if s.id != student_id
                    ]
                if new_cls and new_cls.grade_id:
                    self.cache.students_by_grade[new_cls.grade_id].append(student)

            return Result.success(student)
        except Exception as e:
            return Result.fail(f"更新失败: {e}", ErrorCodes.DATABASE_ERROR)

    def delete(self, student_id: int) -> Result[bool]:
        """删除学生（写 DB + 更新缓存）"""
        try:
            student = self.cache.get_student(student_id)
            if not student:
                return Result.fail("学生不存在", ErrorCodes.STUDENT_NOT_FOUND)

            self.session.delete(student)
            self.session.flush()

            # 同步缓存
            self.cache.students.pop(student_id, None)
            self.cache._deleted_ids.add(student_id)
            cls_id = student.class_id
            if cls_id in self.cache.students_by_class:
                self.cache.students_by_class[cls_id] = [
                    s for s in self.cache.students_by_class[cls_id] if s.id != student_id
                ]
            if student.class_id and student.class_id in self.cache.classes:
                cls = self.cache.classes[student.class_id]
                if cls.grade_id in self.cache.students_by_grade:
                    self.cache.students_by_grade[cls.grade_id] = [
                        s for s in self.cache.students_by_grade[cls.grade_id] if s.id != student_id
                    ]
            self.cache.students_in_school = [
                s for s in self.cache.students_in_school if s.id != student_id
            ]

            return Result.success(True)
        except Exception as e:
            return Result.fail(f"删除失败: {e}", ErrorCodes.DATABASE_ERROR)

    def graduate_class(self, class_id: int) -> Result[int]:
        """班级批量毕业（写 DB + 更新缓存）"""
        try:
            students = self.cache.get_students_by_class(class_id)
            count = 0
            for stu in students:
                if stu.status == "在校":
                    stu.status = "毕业"
                    count += 1
            self.session.flush()
            return Result.success(count)
        except Exception as e:
            return Result.fail(f"毕业操作失败: {e}", ErrorCodes.DATABASE_ERROR)

    def batch_transfer(self, student_ids: list[int], target_class_id: int) -> Result[int]:
        """批量转班（写 DB + 更新缓存）"""
        try:
            target_cls = self.cache.get_class(target_class_id)
            if not target_cls:
                return Result.fail("目标班级不存在", ErrorCodes.CLASS_NOT_FOUND)

            count = 0
            for sid in student_ids:
                student = self.cache.get_student(sid)
                if student and student.class_id != target_class_id:
                    old_cls_id = student.class_id
                    student.class_id = target_class_id
                    count += 1

                    # 同步缓存
                    if old_cls_id in self.cache.students_by_class:
                        self.cache.students_by_class[old_cls_id] = [
                            s for s in self.cache.students_by_class[old_cls_id] if s.id != sid
                        ]
                    self.cache.students_by_class[target_class_id].append(student)

                    # 年级索引
                    old_cls = self.cache.get_class(old_cls_id)
                    if old_cls and old_cls.grade_id in self.cache.students_by_grade:
                        self.cache.students_by_grade[old_cls.grade_id] = [
                            s for s in self.cache.students_by_grade[old_cls.grade_id] if s.id != sid
                        ]
                    if target_cls.grade_id:
                        self.cache.students_by_grade[target_cls.grade_id].append(student)

            self.session.flush()
            return Result.success(count)
        except Exception as e:
            return Result.fail(f"批量转班失败: {e}", ErrorCodes.DATABASE_ERROR)
