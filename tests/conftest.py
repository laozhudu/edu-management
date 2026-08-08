import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

import pytest

from edu_system.api.service_registry import service_registry
from edu_system.database import init_db_with_defaults
from test_data.loader import DataLoader

# 模块级缓存：test 场景数据集（session 级生成一次，function 级复用）
_TEST_DATASET: dict | None = None


def _get_test_dataset() -> dict:
    """获取 test 场景数据集（首次生成并缓存）"""
    global _TEST_DATASET
    if _TEST_DATASET is None:
        from test_data.generate import TestDataGenerator, serialize_test_dataset

        gen = TestDataGenerator(seed=42)
        dataset_obj = gen.generate()
        full = serialize_test_dataset(dataset_obj)
        loader = DataLoader()
        _TEST_DATASET = loader._filter_by_scenario(full, "test")
    return _TEST_DATASET


def _reset_database(full: bool = True) -> None:
    """重建测试数据库（full=True 时删除文件重建，否则仅清数据行）

    full=True: 每个测试前调用（删除+重建+加载 1080 学生 ≈10s）
    full=False: 仅清空数据行（≈0.2s），保留表结构
    """
    import edu_system.database as db
    from edu_system.config import DB_PATH

    # 关闭旧引擎连接并重置
    if db._engine is not None:
        db._engine.dispose()
    db._engine = None
    db._session_factory = None

    # 删除旧 DB 文件（含 WAL/SHM）
    for suffix in ("", "-wal", "-shm"):
        p = Path(DB_PATH)
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass

    # 清理磁盘缓存（diskcache pickle 旧格式可能不兼容 JSONDisk，确保隔离）
    data_dir = Path(DB_PATH).parent
    for cache_db in [
        data_dir / "cache" / "stats" / "cache.db",
        data_dir / "cache" / "http" / "cache.db",
    ]:
        try:
            if cache_db.exists():
                cache_db.unlink()
        except Exception:
            pass

    # 重建 + 加载测试数据
    init_db_with_defaults()
    loader = DataLoader()
    loader.load_version(version="1.0.0", scenario="test")
    # 重新初始化服务注册表
    service_registry._initialized = False
    service_registry.initialize_from_db()


def _clear_data_rows() -> None:
    """仅清空数据行（保留表结构，快速隔离）

    用 DataLoader 的删除逻辑 + 缓存 dataset 快速重载（≈1s，不重复生成）。
    """
    from sqlalchemy import text

    from edu_system.database import get_session

    s = get_session()
    # 按依赖顺序删除（反依赖）
    for table in [
        "leave_applications",
        "student_attendance",
        "scores",
        "class_subjects",
        "exam_subject_settings",
        "student_movements",
        "classrooms",
        "semester_configs",
        "data_locks",
        "students",
        "teachers",
        "classes",
        "exams",
        "semesters",
        "subjects",
        "grades",
        "academic_years",
        "global_settings",
    ]:
        try:
            s.execute(text(f"DELETE FROM {table}"))
        except Exception:
            pass
    try:
        s.execute(text("DELETE FROM sqlite_sequence"))
    except Exception:
        pass  # 无 AUTOINCREMENT 表时 sqlite_sequence 不存在
    s.commit()
    s.close()

    # 用缓存 dataset 重载 test 场景数据
    loader = DataLoader()
    loader.load_version(
        version="1.0.0",
        scenario="test",
        dataset_override=_get_test_dataset(),
    )
    service_registry._initialized = False
    service_registry.initialize_from_db()


@pytest.fixture(scope="session", autouse=True)
def init_test_database(request):
    """Session-scoped: 首次初始化（保持兼容）

    GUI 测试用内存 SQLite，不依赖 school_data.db，豁免。
    """
    if "gui" in request.session.items and all(
        "gui" in item.keywords for item in request.session.items
    ):
        # 纯 GUI 会话：跳过 DB 初始化
        yield
        return
    _reset_database(full=True)
    yield


@pytest.fixture(scope="function", autouse=True)
def isolate_database(request):
    """Function-scoped: 每个测试前清空数据行，保证测试间完全隔离

    仅清行不重建（≈0.2s vs 重建 9.7s），保留表结构与种子数据。
    GUI 测试（pytestmark gui）用内存 SQLite 自带隔离，豁免此重置
    （避免 QApplication + DB 重建并发触发 SIGABRT）。
    """
    if "gui" in request.keywords:
        yield
        return
    _clear_data_rows()
    yield
