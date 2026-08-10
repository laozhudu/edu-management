# ruff: noqa: F405  (star import 自 base.py，__all__ 已保证定义)
"""
report 域模型
"""

from __future__ import annotations

from edu_system.models.base import *  # noqa: F401,F403,F405


# ════════════════════════════════════
# 数据锁定机制
# ════════════════════════════════════
class SemesterStatsCache(Base):
    """学期统计预计算缓存表"""

    __tablename__ = "semester_stats_cache"
    id = Column(Integer, primary_key=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    entity_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="实体类型：student/class/subject/exam/school",
    )
    entity_id = Column(Integer, nullable=False, index=True, comment="实体ID，0表示学期汇总")
    metric_key = Column(
        String(50), nullable=False, index=True, comment="指标键：count/avg_score/pass_rate/rank等"
    )
    metric_value = Column(Float, nullable=False, comment="指标值")
    version = Column(Integer, default=1, comment="缓存版本，重算时递增")
    computed_at = Column(DateTime, server_default=func.now())
    __table_args__ = (
        UniqueConstraint(
            "semester_id", "entity_type", "entity_id", "metric_key", name="uq_semester_stat"
        ),
        Index("idx_stats_semester_entity", "semester_id", "entity_type", "entity_id"),
    )
    semester = relationship("Semester")


# ═══════════════════════════════════
# 字段动态增删机制（Sprint 3.7 核心：灵活度高、耦合低）
# ═══════════════════════════════════


class ReportTemplate(Base):
    """报表模板（M5-D5）：名称/类型/文件路径/版本/变量列表"""

    __tablename__ = "report_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="模板名称")
    template_type = Column(
        String(20), nullable=False, default="excel", comment="excel/word/certificate"
    )
    file_path = Column(String(300), nullable=False, comment="模板文件相对路径")
    version = Column(Integer, nullable=False, default=1, comment="版本号（每次更新+1）")
    variables = Column(Text, nullable=True, comment="变量列表，JSON 数组 [{key,label}]")
    description = Column(String(300), nullable=True, default="")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_by = Column(String(50), nullable=True, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_report_template_version"),
        Index("idx_report_template_name", "name"),
    )


# 通用扩展列混入：各业务表加 ext_json 存自定义字段（SQLite JSON1 支持 json_extract 查询）
def _ext_json_column() -> Column:
    """返回通用 ext_json 扩展列定义（JSON 文本）"""
    return Column(Text, nullable=True, comment="自定义扩展字段（JSON 对象）")


# ════════════════════════════════════
# 字典管理（M1：对齐若依 #6 字典）
# ════════════════════════════════════
