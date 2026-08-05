"""
成绩管理视图加载回归测试（crash 修复：PyQt5.QtChart 缺失）

背景：score.py 顶部硬依赖 PyQt5.QtChart（成绩统计图表），
缺 PyQtChart 包时点开成绩管理直接 ModuleNotFoundError 崩溃
（/home/xsx/.edu_system/crash.log 记录）。

本测试确保：
- score 视图模块可导入（QtChart 已装）
- ScoreView 可实例化（build_view 构造不崩）
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui  # 仅 GUI job（xvfb）运行

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def session():
    """内存 SQLite 会话（最小数据：admin + 学期）"""
    from datetime import date

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.core.permissions import Permission
    from edu_system.models import (
        AcademicYear,
        Base,
        Role,
        Semester,
        SemesterStatus,
        User,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    admin_role = Role(
        name="admin",
        description="管理员",
        permissions=",".join([p.value for p in Permission]),
    )
    s.add(admin_role)
    s.flush()
    s.add(User(username="admin", display_name="管理员", role_id=admin_role.id))

    ay = AcademicYear(name="2024-2025", sort_order=0, is_active=True)
    s.add(ay)
    s.flush()
    sem = Semester(
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
    s.add(sem)
    s.commit()
    yield s
    s.close()


class TestScoreViewLoad:
    def test_score_module_imports(self):
        """score 视图模块可导入（QtChart 依赖已满足）"""
        from edu_system.gui.views import score

        assert score is not None

    def test_score_view_builds(self, qapp, session):
        """ScoreView 可实例化（成绩管理页面打开不崩）"""
        from edu_system.gui.views.score import ScoreView

        view = ScoreView(session)
        assert view is not None
        view.close()

    def test_score_view_registry(self, qapp, session):
        """通过 registry 构建成绩视图（模拟 Workbench 加载路径）"""
        from edu_system.gui.views.registry import VIEW_REGISTRY, build_view

        # 找 score 模块对应的 view_id（score_entry 等）
        score_ids = [vid for vid, (mod, cls, _) in VIEW_REGISTRY.items() if mod.endswith("score")]
        if not score_ids:
            pytest.skip("registry 无成绩视图")
        view = build_view(score_ids[0], session)
        assert view is not None
        view.close()
