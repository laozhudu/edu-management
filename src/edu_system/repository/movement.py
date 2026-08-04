"""
学籍变动仓储
"""

from datetime import date

from edu_system.models import StudentMovement
from edu_system.repository.base import BaseRepository

# 变动类型 → 规范分类映射（move_type → movement_category）
CATEGORY_MAP: dict[str, str] = {
    "升级": "upgrade",
    "留级": "retain",
    "转班": "transfer",
    "休学": "suspend",
    "复学": "resume",
    "转入": "transfer_in",
    "转出": "transfer_out",
    "毕业": "graduate",
    "升学": "upgrade",
}


def normalize_category(move_type: str) -> str:
    """move_type → movement_category 规范化"""
    return CATEGORY_MAP.get(move_type, "")


class MovementRepository(BaseRepository[StudentMovement]):
    def __init__(self, session):
        super().__init__(session, StudentMovement)

    def create_movement(
        self,
        student_id: int,
        semester_id: int,
        move_type: str,
        move_date: date | None = None,
        from_class_id: int | None = None,
        to_class_id: int | None = None,
        reason: str = "",
        operator: str = "",
    ) -> StudentMovement:
        """创建学籍变动记录（自动规范化分类）"""
        mv = StudentMovement(
            student_id=student_id,
            semester_id=semester_id,
            move_type=move_type,
            movement_category=normalize_category(move_type),
            move_date=move_date or date.today(),
            from_class_id=from_class_id,
            to_class_id=to_class_id,
            reason=reason,
            operator=operator,
        )
        self.session.add(mv)
        self.session.commit()
        return mv

    def list_by_student(self, student_id: int) -> list[StudentMovement]:
        return (
            self.session.query(StudentMovement)
            .filter(StudentMovement.student_id == student_id)
            .order_by(StudentMovement.move_date.desc())
            .all()
        )

    def list_by_category(self, category: str, limit: int = 100) -> list[StudentMovement]:
        """按规范分类查询变动记录"""
        return (
            self.session.query(StudentMovement)
            .filter(StudentMovement.movement_category == category)
            .order_by(StudentMovement.move_date.desc())
            .limit(limit)
            .all()
        )

    def list_recent(self, limit: int = 50) -> list[StudentMovement]:
        return (
            self.session.query(StudentMovement)
            .order_by(StudentMovement.created_at.desc())
            .limit(limit)
            .all()
        )
