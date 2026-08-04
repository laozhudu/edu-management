"""
单元测试共享 fixtures
提供 db_session fixture，供核心模块测试复用
"""

import pytest


@pytest.fixture
def db_session():
    """提供数据库 session"""
    from edu_system.database import get_session

    session = get_session()
    yield session
    session.close()
