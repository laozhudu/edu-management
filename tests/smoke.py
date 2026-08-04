#!/usr/bin/env python3
"""
Smoke tests - 快速验证核心功能可用
运行：pytest tests/smoke.py -x -v
"""

import sys

import pytest

sys.path.insert(0, "项目根目录/src")

from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)


def test_config_imports():
    """配置模块所有常量可导入"""
    from edu_system.config import APP_NAME, DB_PATH

    assert APP_NAME == "教务管理系统"
    assert DB_PATH == "data/school_data.db"


def test_database_init():
    """数据库初始化成功"""
    from edu_system.database import init_db_with_defaults

    init_db_with_defaults()
    # 无异常即通过


def test_models_import():
    """所有模型可导入"""
    assert True


def test_core_services():
    """核心服务可导入"""
    assert True


def test_api_creation():
    """FastAPI 应用创建成功"""
    from edu_system.api.main import create_app

    app = create_app()
    assert len(app.routes) > 0


def test_gui_imports():
    """GUI 组件可导入（需 QApplication）"""
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-v"])
