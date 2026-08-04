"""学籍变动服务 — 含升年级模块
升年级规则：
  初三→毕业(状态改毕业，班级保留)  初二→初三(class_id 2xx→3xx)
  初一→初二(class_id 1xx→2xx)  创建空初一班(101~110)
防呆：执行前备份 DB、展示明细、事务回滚
"""

import os
import shutil
from datetime import date

from sqlalchemy.orm import Session

from edu_system.config import DB_PATH
from edu_system.core import Permission, require_permission
from edu_system.core.audit import manual_audit
from edu_system.core.events import DomainEvent, EventBus
from edu_system.models import Class as ClassModel
from edu_system.models import Grade, Semester, Student, StudentMovement


class EnrollmentService:
    def __init__(self, session: Session):
        self.session = session

    @require_permission(Permission.STUDENT_EDIT)
    def transfer(self, student_id: int, to_class_id: int, reason: str = "") -> StudentMovement:
        student = self.session.get(Student, student_id)
        if not student:
            raise ValueError(f"学生不存在: {student_id}")
        old_class_id = student.class_id
        movement = StudentMovement(
            student_id=student_id,
            move_type="转班",
            move_date=date.today(),
            from_class_id=student.class_id,
            to_class_id=to_class_id,
            reason=reason,
        )
        student.class_id = to_class_id
        self.session.add(movement)
        self.session.flush()

        # 审计日志
        manual_audit(
            self.session,
            "students",
            student_id,
            "TRANSFER",
            {"class_id": old_class_id},
            {"class_id": to_class_id},
        )

        # 发布领域事件
        EventBus.publish(
            DomainEvent(
                "student.transferred",
                {
                    "student_id": student_id,
                    "from_class_id": student.class_id,
                    "to_class_id": to_class_id,
                    "reason": reason,
                    "movement_id": movement.id,
                },
            )
        )

        return movement

    @require_permission(Permission.STUDENT_EDIT)
    def change_status(self, student_id: int, new_status: str, reason: str = "") -> StudentMovement:
        """
        修改学生状态，带状态机校验
        有效转换：
          在校 → 休学/退学/转学/毕业
          休学 → 在校(复学)/退学/转学
          转学 → (终态)
          退学 → (终态)
          毕业 → (终态)
        """
        # 状态机定义：当前状态 -> 允许的目标状态
        STATE_TRANSITIONS = {
            "在校": {"休学", "退学", "转学", "毕业"},
            "休学": {"在校", "退学", "转学"},  # 复学 = 回到在校
            "转学": set(),  # 终态
            "退学": set(),  # 终态
            "毕业": set(),  # 终态
        }

        # 处理"复学"别名 -> 实际上是设为"在校"
        if new_status == "复学":
            new_status = "在校"

        valid_statuses = {"在校", "休学", "退学", "转学", "毕业"}
        if new_status not in valid_statuses:
            raise ValueError(f"无效状态: {new_status}")

        student = self.session.get(Student, student_id)
        if not student:
            raise ValueError(f"学生不存在: {student_id}")

        old_status = student.status

        # 同态不处理（需在状态机校验前）
        if old_status == new_status:
            return None

        # 状态机校验
        allowed = STATE_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"状态流转不允许: {old_status} → {new_status}。允许: {allowed or '无(终态)'}"
            )

        movement = StudentMovement(
            student_id=student_id,
            move_type=new_status,
            move_date=date.today(),
            from_class_id=student.class_id,
            to_class_id=student.class_id,
            reason=reason,
        )
        student.status = new_status
        self.session.add(movement)
        self.session.flush()

        # 审计日志
        manual_audit(
            self.session,
            "students",
            student_id,
            "STATUS_CHANGE",
            {"status": old_status},
            {"status": new_status},
        )

        # 发布领域事件
        EventBus.publish(
            DomainEvent(
                "student.status_changed",
                {
                    "student_id": student_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": reason,
                    "movement_id": movement.id,
                },
            )
        )

        return movement

    @require_permission(Permission.ENROLLMENT_UPGRADE)
    def promote_grade(self, new_semester: Semester, old_semester: Semester) -> dict:
        """
        升年级主流程。
        返回 {"backup": path, "graduated": N, "to_g3": N, "to_g2": N, "new_classes": N}
        """
        # ① 备份数据库（防呆）
        backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(
            backup_dir, f"before_promote_{old_semester.year_start}_{old_semester.semester}.db"
        )
        shutil.copy2(DB_PATH, backup_path)

        result = {"backup": backup_path, "graduated": 0, "to_g3": 0, "to_g2": 0, "new_classes": 0}

        try:
            # ② 初三→毕业（改状态，班级不变）
            g3 = self.session.query(Grade).filter_by(name="初三级").first()
            if g3:
                classes_g3 = self.session.query(ClassModel).filter_by(grade_id=g3.id).all()
                for cls in classes_g3:
                    students = (
                        self.session.query(Student).filter_by(class_id=cls.id, status="在校").all()
                    )
                    for stu in students:
                        self.session.add(
                            StudentMovement(
                                student_id=stu.id,
                                semester_id=new_semester.id,
                                move_type="毕业",
                                move_date=date.today(),
                                from_class_id=stu.class_id,
                                to_class_id=stu.class_id,
                                reason=f"升年级({old_semester.label}→{new_semester.label})",
                            )
                        )
                        stu.status = "毕业"
                        result["graduated"] += 1

            # ③ 初二→初三（改 class_id 2xx→3xx）
            g2 = self.session.query(Grade).filter_by(name="初二级").first()
            if g2 and g3:
                classes_g2 = self.session.query(ClassModel).filter_by(grade_id=g2.id).all()
                for cls in classes_g2:
                    old_name = cls.name
                    new_name = f"3{old_name[1:]}"
                    target_cls = (
                        self.session.query(ClassModel)
                        .filter_by(grade_id=g3.id, name=new_name)
                        .first()
                    )
                    if not target_cls:
                        target_cls = ClassModel(
                            grade_id=g3.id,
                            name=new_name,
                            academic_year=new_semester.year_start,
                            semester_name=new_semester.semester,
                        )
                        self.session.add(target_cls)
                        self.session.flush()
                    students = (
                        self.session.query(Student).filter_by(class_id=cls.id, status="在校").all()
                    )
                    for stu in students:
                        self.session.add(
                            StudentMovement(
                                student_id=stu.id,
                                semester_id=new_semester.id,
                                move_type="升年级",
                                move_date=date.today(),
                                from_class_id=stu.class_id,
                                to_class_id=target_cls.id,
                                reason="初二→初三",
                            )
                        )
                        stu.class_id = target_cls.id
                        result["to_g3"] += 1

            # ④ 初一→初二（改 class_id 1xx→2xx）
            g1 = self.session.query(Grade).filter_by(name="初一级").first()
            if g1 and g2:
                classes_g1 = self.session.query(ClassModel).filter_by(grade_id=g1.id).all()
                for cls in classes_g1:
                    old_name = cls.name
                    new_name = f"2{old_name[1:]}"
                    target_cls = (
                        self.session.query(ClassModel)
                        .filter_by(grade_id=g2.id, name=new_name)
                        .first()
                    )
                    if not target_cls:
                        target_cls = ClassModel(
                            grade_id=g2.id,
                            name=new_name,
                            academic_year=new_semester.year_start,
                            semester_name=new_semester.semester,
                        )
                        self.session.add(target_cls)
                        self.session.flush()
                    students = (
                        self.session.query(Student).filter_by(class_id=cls.id, status="在校").all()
                    )
                    for stu in students:
                        self.session.add(
                            StudentMovement(
                                student_id=stu.id,
                                semester_id=new_semester.id,
                                move_type="升年级",
                                move_date=date.today(),
                                from_class_id=stu.class_id,
                                to_class_id=target_cls.id,
                                reason="初一→初二",
                            )
                        )
                        stu.class_id = target_cls.id
                        result["to_g2"] += 1

            # ⑤ 创建新初一空班
            if g1:
                for i in range(1, 11):
                    existing = (
                        self.session.query(ClassModel)
                        .filter_by(grade_id=g1.id, name=f"1{i:02d}")
                        .first()
                    )
                    if not existing:
                        self.session.add(
                            ClassModel(
                                grade_id=g1.id,
                                name=f"1{i:02d}",
                                academic_year=new_semester.year_start,
                                semester_name=new_semester.semester,
                            )
                        )
                        result["new_classes"] += 1

            # ⑥ 更新旧学期状态
            old_semester.is_active = False
            if old_semester.semester == "2":
                old_semester.status = SemesterStatus.archived
            else:
                old_semester.status = SemesterStatus.archived

            self.session.flush()

            # 审计日志
            manual_audit(
                self.session,
                "semesters",
                old_semester.id,
                "PROMOTE_GRADE",
                {
                    "is_active": True,
                    "status": (
                        old_semester.status.value
                        if hasattr(old_semester.status, "value")
                        else old_semester.status
                    ),
                },
                {"is_active": False, "status": "archived"},
            )

            # 发布领域事件
            EventBus.publish(
                DomainEvent(
                    "grade.promoted",
                    {
                        "old_semester_id": old_semester.id,
                        "new_semester_id": new_semester.id,
                        "result": result,
                    },
                )
            )

            return result

        except Exception:
            self.session.rollback()
            raise

    def promote_summary(self, old_semester: Semester) -> dict:
        """预览升年级影响（不执行）"""
        result = {"graduated": 0, "to_g3": 0, "to_g2": 0, "new_classes": 10}
        g3 = self.session.query(Grade).filter_by(name="初三级").first()
        if g3:
            for cls in self.session.query(ClassModel).filter_by(grade_id=g3.id).all():
                result["graduated"] += (
                    self.session.query(Student).filter_by(class_id=cls.id, status="在校").count()
                )
        g2 = self.session.query(Grade).filter_by(name="初二级").first()
        if g2:
            for cls in self.session.query(ClassModel).filter_by(grade_id=g2.id).all():
                result["to_g3"] += (
                    self.session.query(Student).filter_by(class_id=cls.id, status="在校").count()
                )
        g1 = self.session.query(Grade).filter_by(name="初一级").first()
        if g1:
            for cls in self.session.query(ClassModel).filter_by(grade_id=g1.id).all():
                result["to_g2"] += (
                    self.session.query(Student).filter_by(class_id=cls.id, status="在校").count()
                )
        return result


class PromotionWizard:
    """升年级向导：预览 → 确认备份 → 执行 → 结果报表"""

    def __init__(self, session):
        self.session = session
        self._svc = EnrollmentService(session)
        self._old_semester = None
        self._new_semester = None
        self._summary = None

    def run(self):
        """执行完整向导流程，返回 (success: bool, result: dict)"""
        # 1. 获取当前/上一学期
        cur = self.session.query(Semester).filter_by(is_active=True).first()
        old = None
        if cur:
            old = (
                self.session.query(Semester)
                .filter(Semester.id != cur.id, Semester.year_start < cur.year_start)
                .order_by(Semester.year_start.desc())
                .first()
            )

        if not cur or not old:
            return False, {"error": "需要至少两个学期才能升年级"}

        self._old_semester = old
        self._new_semester = cur

        # 2. 预览摘要
        self._summary = self._svc.promote_summary(old)

        # 3. 备份
        backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"before_promote_{old.year_start}_{old.semester}.db")
        shutil.copy2(DB_PATH, backup_path)

        # 4. 执行
        try:
            result = self._svc.promote_grade(cur, old)
            result["backup"] = backup_path
            self.session.commit()
            return True, result
        except Exception as e:
            self.session.rollback()
            return False, {"error": str(e)}
