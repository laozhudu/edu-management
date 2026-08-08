"""
统一结果模型 - 所有 Service 方法返回 Result[T]
避免异常流控制业务逻辑，显式处理成功/失败
"""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    """统一返回结果"""

    ok: bool
    data: T | None = None
    error: str | None = None
    code: str = ""  # 业务错误码：STUDENT_NOT_FOUND / DUPLICATE_EXAM_NO / VALIDATION_ERROR ...

    @staticmethod
    def success(data: T) -> "Result[T]":
        return Result(ok=True, data=data)

    @staticmethod
    def fail(error: str, code: str = "") -> "Result[T]":
        return Result(ok=False, error=error, code=code)

    def unwrap(self) -> T:
        """成功时返回数据，失败抛异常（仅用于确信必成功的场景）"""
        if not self.ok:
            raise RuntimeError(f"Result unwrap failed: {self.error} [{self.code}]")
        if self.data is None:
            raise RuntimeError(f"Result unwrap failed: data is None [{self.code}]")
        return self.data


# 常用错误码常量
class ErrorCodes:
    # 学生相关
    STUDENT_NOT_FOUND = "STUDENT_NOT_FOUND"
    DUPLICATE_STUDENT_CODE = "DUPLICATE_STUDENT_CODE"
    DUPLICATE_ID_CARD = "DUPLICATE_ID_CARD"
    DUPLICATE_EXAM_NO = "DUPLICATE_EXAM_NO"
    INVALID_STUDENT_STATUS = "INVALID_STUDENT_STATUS"

    # 班级相关
    CLASS_NOT_FOUND = "CLASS_NOT_FOUND"
    CLASS_FULL = "CLASS_FULL"

    # 成绩相关
    SCORE_NOT_FOUND = "SCORE_NOT_FOUND"
    DUPLICATE_SCORE = "DUPLICATE_SCORE"
    INVALID_SCORE_RANGE = "INVALID_SCORE_RANGE"

    # 考试相关
    EXAM_NOT_FOUND = "EXAM_NOT_FOUND"
    EXAM_ALREADY_PUBLISHED = "EXAM_ALREADY_PUBLISHED"

    # 学籍变动
    INVALID_MOVE_TYPE = "INVALID_MOVE_TYPE"

    # 通用
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    DATABASE_ERROR = "DATABASE_ERROR"
