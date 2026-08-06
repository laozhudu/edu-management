"""
数据库引擎与会话管理
优化项：
1. SQLite WAL 模式 + mmap + 大缓存
2. 连接池预热
3. 实用 PRAGMA 优化
4. 学期上下文自动注入（通过自定义 Query 类）
"""

import threading
from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Query, Session, sessionmaker
from sqlalchemy.pool import NullPool

from edu_system.config import settings
from edu_system.core.audit import audit_init
from edu_system.models import Base

# 全局引擎单例
_engine = None
_session_factory = None

# 线程局部存储：当前激活的学期/校区/用户上下文
_thread_local = threading.local()


def _create_engine():
    """创建引擎"""
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        # 并发访问：每 session 独立连接（SQLite 多连接 + WAL 并发写）
        # StaticPool 单连接仅适合单线程桌面；API 服务需多连接
        poolclass=NullPool,  # 每操作新连接，避免连接复用竞争
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
    )
    return engine


def get_engine():
    """获取全局引擎单例，首次调用时预热"""
    global _engine
    if _engine is None:
        _engine = _create_engine()
        # 预热：建立连接并执行关键 PRAGMA
        with _engine.connect() as conn:
            # 1. WAL 模式 - 写不阻塞读，并发 +300%
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            # 2. 同步模式 NORMAL - 安全+性能平衡
            conn.execute(text("PRAGMA synchronous=NORMAL;"))
            # 3. 32MB page cache (负数=KB)
            conn.execute(text("PRAGMA cache_size=-32768;"))
            # 4. 256MB mmap，内核直接映射文件
            conn.execute(text("PRAGMA mmap_size=268435456;"))
            # 5. 4KB page，减少 IO
            conn.execute(text("PRAGMA page_size=4096;"))
            # 6. 5秒超时
            conn.execute(text("PRAGMA busy_timeout=5000;"))
            # 7. 临时表内存
            conn.execute(text("PRAGMA temp_store=MEMORY;"))
            # 8. WAL 日志限制 64MB
            conn.execute(text("PRAGMA journal_size_limit=67108864;"))
            # 强制 checkpoint，确保 WAL 生效
            conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
            # 简单查询预热
            conn.execute(text("SELECT 1;"))

            # 验证优化生效
            result = conn.execute(text("PRAGMA journal_mode;")).fetchone()
            print(f"[DB] Journal mode: {result[0] if result else 'unknown'}")
            result = conn.execute(text("PRAGMA cache_size;")).fetchone()
            print(f"[DB] Cache size: {result[0] if result else 'unknown'} pages")
            result = conn.execute(text("PRAGMA mmap_size;")).fetchone()
            print(f"[DB] Mmap size: {result[0] if result else 'unknown'} bytes")
            result = conn.execute(text("PRAGMA page_size;")).fetchone()
            print(f"[DB] Page size: {result[0] if result else 'unknown'} bytes")
            result = conn.execute(text("PRAGMA synchronous;")).fetchone()
            print(f"[DB] Synchronous: {result[0] if result else 'unknown'}")
    # 初始化审计监听器
    audit_init(_engine)
    return _engine


def get_session_factory():
    """获取会话工厂"""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _session_factory


def get_session() -> Session:
    """获取数据库会话（上下文管理器用）"""
    return get_session_factory()()


# ============================================================
# 学期/校区/用户上下文管理 + 自动过滤注入
# ============================================================


def set_active_semester(semester_id: int):
    """设置当前线程的激活学期"""
    _thread_local.active_semester_id = semester_id


def get_active_semester() -> int:
    """获取当前线程的激活学期，默认 0 表示无"""
    return getattr(_thread_local, "active_semester_id", 0)


def set_active_school(school_id: int):
    _thread_local.active_school_id = school_id


def get_active_school() -> int:
    return getattr(_thread_local, "active_school_id", 1)


def set_current_user(user_id: int, role_codes: list | None = None):
    _thread_local.current_user_id = user_id
    _thread_local.current_role_codes = role_codes or []


def get_current_user_id() -> int:
    return getattr(_thread_local, "current_user_id", 0)


def get_current_role_codes() -> list:
    return getattr(_thread_local, "current_role_codes", [])


@contextmanager
def semester_context(semester_id: int):
    """学期上下文管理器：临时切换学期，退出自动恢复"""
    old = get_active_semester()
    set_active_semester(semester_id)
    try:
        yield
    finally:
        set_active_semester(old)


# SQLAlchemy 事件：自动注入 semester_id / school_id 过滤（在 Query 编译前）
@event.listens_for(Query, "before_compile", retval=True)
def _inject_semester_filter(query):
    """自动给查询注入 semester_id / school_id 过滤条件

    规则：
    1. 已有 semester_id/school_id 条件的查询不再注入
    2. 标记了 _skip_semester_filter 的查询跳过（跨学期报表、管理员全局视图）
    3. 仅对包含 semester_id/school_id 列的表注入
    """
    # 检查是否跳过
    if getattr(query, "_skip_semester_filter", False):
        return query

    # 已有 LIMIT/OFFSET 的查询跳过注入（.first()/.limit() 场景，
    # 此时再 filter 会抛 "Query already has LIMIT or OFFSET applied"）
    if query._limit_clause is not None or query._offset_clause is not None:
        return query

    # 获取当前上下文
    sem_id = get_active_semester()
    sch_id = get_active_school()
    if sem_id == 0 and sch_id == 1:
        return query  # 无激活学期，不注入

    # 遍历查询涉及的实体（使用 column_descriptions 获取实体信息，兼容 SQLAlchemy 2.0）
    entities = query.column_descriptions
    if not entities:
        return query

    for entity_desc in entities:
        entity = entity_desc.get("entity")
        if entity and hasattr(entity, "__mapper__"):
            mapper = entity.__mapper__
            cols = mapper.columns

            # 注入 semester_id 过滤
            if "semester_id" in cols and sem_id != 0:
                # 检查是否已有 semester_id 过滤条件
                has_filter = False
                for criterion in query._where_criteria:
                    if _has_column_filter(criterion, "semester_id"):
                        has_filter = True
                        break
                if not has_filter:
                    query = query.filter(cols.semester_id == sem_id)

            # 注入 school_id 过滤
            if "school_id" in cols and sch_id != 1:
                has_filter = False
                for criterion in query._where_criteria:
                    if _has_column_filter(criterion, "school_id"):
                        has_filter = True
                        break
                if not has_filter:
                    query = query.filter(cols.school_id == sch_id)

    return query


def _has_column_filter(criterion, column_name: str) -> bool:
    """递归检查过滤条件中是否包含指定列"""
    from sqlalchemy.sql.elements import BinaryExpression, UnaryExpression

    if isinstance(criterion, BinaryExpression):
        left = criterion.left
        right = criterion.right
        if hasattr(left, "name") and left.name == column_name:
            return True
        if hasattr(right, "name") and right.name == column_name:
            return True
    elif isinstance(criterion, UnaryExpression):
        return _has_column_filter(criterion.element, column_name)
    elif hasattr(criterion, "clauses"):  # and_ / or_
        for clause in criterion.clauses:
            if _has_column_filter(clause, column_name):
                return True
    return False


# SQLite 外键级联必须手动开启
@event.listens_for(get_engine(), "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def init_db() -> None:
    """初始化数据库（建表+约束）"""
    Base.metadata.create_all(get_engine())
    # SQLite 不自动创建唯一约束索引，手动添加
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_student_code "
                "ON students(student_code) WHERE student_code != ''"
            )
        )


def init_db_with_defaults() -> None:
    """初始化数据库 + 写入默认数据"""
    init_db()
    with get_session() as session:
        _ensure_defaults(session)
        session.commit()


def _ensure_defaults(session: Session) -> None:
    """确保默认数据存在"""

    from edu_system.models import (
        AcademicYear,
        GlobalSetting,
        Grade,
        School,
        Semester,
        SemesterStatus,
        Subject,
    )

    # 默认年级
    for i, name in enumerate(["初一级", "初二级", "初三级"]):
        if not session.query(Grade).filter_by(name=name).first():
            session.add(Grade(name=name, sort_order=i))

    # 默认科目
    defaults = [
        ("语文", 120, 72, 84, 96, 36),
        ("数学", 120, 72, 84, 96, 36),
        ("英语", 120, 72, 84, 96, 36),
        ("政治", 80, 48, 56, 64, 24),
        ("物理", 100, 60, 70, 80, 30),
        ("化学", 80, 48, 56, 64, 24),
        ("历史", 80, 48, 56, 64, 24),
        ("地理", 100, 60, 70, 80, 30),
        ("生物", 100, 60, 70, 80, 30),
        ("体育", 70, 42, 49, 56, 21),
    ]
    for i, (name, fm, pl, gl, el, ll) in enumerate(defaults):
        if not session.query(Subject).filter_by(name=name).first():
            session.add(
                Subject(
                    name=name,
                    full_mark=fm,
                    pass_line=pl,
                    good_line=gl,
                    excellent_line=el,
                    low_line=ll,
                    sort_order=i,
                )
            )

    # 默认缺考标记
    if not session.query(GlobalSetting).filter_by(key="absent_marks").first():
        session.add(GlobalSetting(key="absent_marks", value="-1,0"))

    # 默认学年/学期
    ay = session.query(AcademicYear).filter_by(name="2024-2025").first()
    if not ay:
        ay = AcademicYear(
            name="2024-2025", sort_order=0, is_active=True, description="2024-2025 学年"
        )
        session.add(ay)
        session.flush()

    sem1 = session.query(Semester).filter_by(academic_year_id=ay.id, semester="1").first()
    if not sem1:
        sem1 = Semester(
            academic_year_id=ay.id,
            year_start=2024,
            semester="1",
            label="2024-2025 第1学期",
            sort_order=1,
            is_active=True,
            status=SemesterStatus.active,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 1, 15),
        )
        session.add(sem1)
        session.flush()

    sem2 = session.query(Semester).filter_by(academic_year_id=ay.id, semester="2").first()
    if not sem2:
        sem2 = Semester(
            academic_year_id=ay.id,
            year_start=2024,
            semester="2",
            label="2024-2025 第2学期",
            sort_order=2,
            is_active=False,
            status=SemesterStatus.draft,
            start_date=date(2025, 2, 15),
            end_date=date(2025, 7, 15),
        )
        session.add(sem2)
        session.flush()

    # 激活默认学期
    set_active_semester(int(sem1.id))

    # 默认角色
    from edu_system.core.auth import get_password_hash
    from edu_system.core.permissions import ROLE_PERMISSIONS
    from edu_system.models import Role, User

    if not session.query(Role).first():
        for name, perms in ROLE_PERMISSIONS.items():
            session.add(
                Role(
                    name=name,
                    description={
                        "admin": "管理员",
                        "director": "教务主任",
                        "teacher": "教师",
                        "reader": "只读",
                    }.get(name, ""),
                    permissions=",".join(sorted(perms)),
                )
            )
    if not session.query(User).first():
        admin_role = session.query(Role).filter_by(name="admin").first()
        session.add(
            User(
                username="admin",
                password_hash=get_password_hash("admin123"),  # 使用 bcrypt 哈希
                display_name="系统管理员",
                role_id=admin_role.id if admin_role else None,
            )
        )

    # 默认校区（校名从 ui_config 配置读取，可在配置灵活修改）
    if not session.query(School).first():
        from edu_system.config.ui_config import get_config

        _cfg = get_config()
        _school_name = getattr(_cfg, "school_name", "示例学校") or "示例学校"
        session.add(School(name=_school_name, code="cnzx", config_json="{}", is_active=True))

    # 默认缺考标记
    from edu_system.models import GlobalSetting

    if not session.query(GlobalSetting).filter_by(key="absent_marks").first():
        session.add(GlobalSetting(key="absent_marks", value="-1,0"))


# SQLite 外键级联必须手动开启
@event.listens_for(get_engine(), "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
