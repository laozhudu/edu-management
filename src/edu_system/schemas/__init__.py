"""
分页/筛选/排序 标准化协议
所有 Repository 查询统一使用 PageRequest / PageResponse

同时保留兼容旧代码的 StudentFilter
"""

import re
from datetime import date
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


# 正则验证模式
PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")
ID_CARD_REGEX = re.compile(r"^\d{17}[\dXx]$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class SortOrder(BaseModel):
    """排序字段"""

    field: str = ""
    desc: bool = False


class FilterOperator(BaseModel):
    """过滤操作符"""

    field: str = ""
    operator: str = "eq"  # eq/ne/gt/gte/lt/lte/like/ilike/in/not_in/between
    value: Any = None
    value2: Any = None  # for between


class PageRequest(BaseModel):
    """分页请求 - 所有列表查询统一入口"""

    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(50, ge=1, le=500, description="每页条数")
    sort: list[SortOrder] = Field(default_factory=list, description="排序")
    filters: list[FilterOperator] = Field(default_factory=list, description="过滤条件")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PageResponse(BaseModel, Generic[T]):
    """分页响应 - 所有列表查询统一出口"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def create(cls, items: list[T], total: int, request: PageRequest) -> "PageResponse[T]":
        total_pages = (total + request.page_size - 1) // request.page_size
        return cls(
            items=items,
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
        )


# ============ 兼容旧代码的 Filter ============


class StudentFilter(BaseModel):
    """学生筛选参数（兼容旧代码）"""

    grade: str = ""
    class_name: str = ""
    status: str = ""
    keyword: str = ""


class StudentPageRequest(PageRequest):
    """学生列表分页请求"""

    # 业务字段作为便捷属性，会自动转换为 filters
    grade: str = ""
    class_name: str = ""
    status: str = ""
    keyword: str = ""

    def to_generic(self) -> PageRequest:
        """转换为通用 PageRequest"""
        filters = []
        if self.grade:
            grade_prefix = {"初一级": "1", "初二级": "2", "初三级": "3"}.get(self.grade, "")
            if grade_prefix:
                filters.append(
                    FilterOperator(field="class_name", operator="like", value=f"{grade_prefix}%")
                )
        if self.class_name:
            filters.append(FilterOperator(field="class_name", operator="eq", value=self.class_name))
        if self.status:
            filters.append(FilterOperator(field="status", operator="eq", value=self.status))
        if self.keyword:
            kw = f"%{self.keyword}%"
            filters.append(FilterOperator(field="name", operator="like", value=kw))

        return PageRequest(
            page=self.page,
            page_size=self.page_size,
            sort=self.sort,
            filters=filters,
        )


class TeacherPageRequest(PageRequest):
    """教师列表分页请求"""

    status: str = ""
    subject_id: int | None = None
    keyword: str = ""

    def to_generic(self) -> PageRequest:
        filters = []
        if self.status:
            filters.append(FilterOperator(field="status", operator="eq", value=self.status))
        if self.subject_id:
            filters.append(FilterOperator(field="subject_id", operator="eq", value=self.subject_id))
        if self.keyword:
            kw = f"%{self.keyword}%"
            filters.append(FilterOperator(field="name", operator="like", value=kw))
        return PageRequest(
            page=self.page,
            page_size=self.page_size,
            sort=self.sort,
            filters=filters,
        )


class ExamPageRequest(PageRequest):
    """考试列表分页请求"""

    semester_id: int | None = None
    status: str = ""
    exam_type: str = ""
    grade_start: int | None = None
    grade_end: int | None = None
    keyword: str = ""

    def to_generic(self) -> PageRequest:
        filters = []
        if self.semester_id:
            filters.append(
                FilterOperator(field="semester_id", operator="eq", value=self.semester_id)
            )
        if self.status:
            filters.append(FilterOperator(field="status", operator="eq", value=self.status))
        if self.exam_type:
            filters.append(FilterOperator(field="exam_type", operator="eq", value=self.exam_type))
        if self.grade_start:
            filters.append(
                FilterOperator(field="grade_start", operator="gte", value=self.grade_start)
            )
        if self.grade_end:
            filters.append(FilterOperator(field="grade_end", operator="lte", value=self.grade_end))
        if self.keyword:
            kw = f"%{self.keyword}%"
            filters.append(FilterOperator(field="name", operator="like", value=kw))
        return PageRequest(
            page=self.page,
            page_size=self.page_size,
            sort=self.sort,
            filters=filters,
        )


class ScorePageRequest(PageRequest):
    """成绩列表分页请求"""

    exam_id: int | None = None
    class_id: int | None = None
    subject_id: int | None = None
    student_id: int | None = None

    def to_generic(self) -> PageRequest:
        filters = []
        if self.exam_id:
            filters.append(FilterOperator(field="exam_id", operator="eq", value=self.exam_id))
        if self.class_id:
            filters.append(FilterOperator(field="class_id", operator="eq", value=self.class_id))
        if self.subject_id:
            filters.append(FilterOperator(field="subject_id", operator="eq", value=self.subject_id))
        if self.student_id:
            filters.append(FilterOperator(field="student_id", operator="eq", value=self.student_id))
        return PageRequest(
            page=self.page,
            page_size=self.page_size,
            sort=self.sort,
            filters=filters,
        )


# ============ DTO 基类 ============


class BaseDTO(BaseModel):
    """基础 DTO"""

    pass


class StudentCreateDTO(BaseModel):
    """创建学生"""

    name: str
    class_name: str
    student_no: str = ""
    gender: str = ""
    id_card: str = ""
    phone: str = ""
    birth_date: str | None = None
    ethnicity: str = ""
    address: str = ""
    enroll_year: int = 0
    boarding: str = "走读"
    status: str = "在校"
    note: str = ""
    guardian1_name: str = ""
    guardian1_phone: str = ""
    guardian2_name: str = ""
    guardian2_phone: str = ""

    # 验证器
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if v and not PHONE_REGEX.match(v):
            raise ValueError("手机号格式不正确（需11位，以13-19开头）")
        return v

    @field_validator("id_card")
    @classmethod
    def validate_id_card(cls, v: str) -> str:
        if v and not ID_CARD_REGEX.match(v):
            raise ValueError("身份证号格式不正确（需18位，最后一位可为X）")
        return v

    @field_validator("guardian1_phone", "guardian2_phone")
    @classmethod
    def validate_guardian_phone(cls, v: str) -> str:
        if v and not PHONE_REGEX.match(v):
            raise ValueError("监护人手机号格式不正确（需11位，以13-19开头）")
        return v


class StudentUpdateDTO(BaseModel):
    """更新学生（所有字段可选）"""

    name: str | None = None
    student_no: str | None = None
    gender: str | None = None
    id_card: str | None = None
    phone: str | None = None
    birth_date: str | None = None
    ethnicity: str | None = None
    address: str | None = None
    boarding: str | None = None
    status: str | None = None
    note: str | None = None
    guardian1_name: str | None = None
    guardian1_phone: str | None = None
    guardian2_name: str | None = None
    guardian2_phone: str | None = None

    # 验证器
    @field_validator("phone", "guardian1_phone", "guardian2_phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v and not PHONE_REGEX.match(v):
            raise ValueError("手机号格式不正确（需11位，以13-19开头）")
        return v

    @field_validator("id_card")
    @classmethod
    def validate_id_card(cls, v: str | None) -> str | None:
        if v and not ID_CARD_REGEX.match(v):
            raise ValueError("身份证号格式不正确（需18位，最后一位可为X）")
        return v


class TeacherCreateDTO(BaseModel):
    """创建教师"""

    name: str
    gender: str = ""
    phone: str = ""
    title: str = ""
    education: str = ""
    degree: str = ""
    political_status: str = ""
    birth_date: str | None = None
    work_start_date: str | None = None
    graduation_date: str | None = None
    staff_no: str = ""
    note: str = ""


class ClassCreateDTO(BaseModel):
    """创建班级"""

    name: str  # 如 "101"
    grade_id: int
    head_teacher_id: int | None = None
    capacity: int = 50
    room: str = ""
    class_type: str = ""


class ExamCreateDTO(BaseModel):
    """创建考试"""

    semester_id: int
    name: str
    exam_date: str | None = None
    grade_start: int | None = None
    grade_end: int | None = None
    exam_type: str = "final"
    note: str = ""


class SubjectCreateDTO(BaseModel):
    """创建科目"""

    name: str
    full_mark: float = 100
    pass_line: float = 60
    good_line: float = 80
    excellent_line: float = 90
    low_line: float = 30
    sort_order: int = 0
    credit: float = 1.0
    weight: float = 1.0
    is_core: bool = True
    exam_type: str = "normal"


class MovementCreateDTO(BaseModel):
    """学籍变动"""

    student_name: str
    class_name: str
    move_type: str  # 转班/休学/复学/退学/毕业/转入/转出
    target_class: str | None = None
    reason: str = ""
    move_date: str | None = None


# ============ 导出导入 DTO ============


class ImportPreviewRow(BaseModel):
    """导入预览行"""

    row_num: int
    data: dict[str, Any]
    status: str  # new/update/conflict/error
    message: str = ""
    existing_id: int | None = None


class ImportPreviewResponse(BaseModel):
    """导入预览响应"""

    total_rows: int
    new_count: int
    update_count: int
    conflict_count: int
    error_count: int
    rows: list[ImportPreviewRow]


class ExportRequest(BaseModel):
    """导出请求"""

    entity: str  # student/teacher/class/exam/score
    columns: list[str] = []  # 空则全选
    filters: dict[str, Any] = Field(default_factory=dict)
    format: str = "xlsx"  # xlsx/csv
