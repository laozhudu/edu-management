"""
Feature Flag 单元测试
验证：基础开关、角色灰度、百分比灰度、热加载、装饰器
"""

import json

import pytest

from edu_system.core.features import FeatureFlags, feature_flag


@pytest.fixture
def temp_config(tmp_path):
    """创建临时 features.json 配置"""
    config = {
        "flag_on": {"enabled": True, "percentage": 100},
        "flag_off": {"enabled": False},
        "flag_role": {"enabled": True, "roles": ["admin"]},
        "flag_percent": {"enabled": True, "percentage": 50},
        "flag_users": {"enabled": True, "users": [1, 2, 3]},
        "flag_school": {"enabled": True, "schools": [1]},
    }
    path = tmp_path / "features.json"
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def patch_config_path(temp_config, monkeypatch):
    """将 FeatureFlags 配置路径指向临时文件"""
    monkeypatch.setattr(FeatureFlags, "_config_path", temp_config)
    # 强制重载
    FeatureFlags.reload()


def test_enabled_flag():
    """启用 flag 返回 True"""
    assert FeatureFlags.is_enabled("flag_on") is True


def test_disabled_flag():
    """禁用 flag 返回 False"""
    assert FeatureFlags.is_enabled("flag_off") is False


def test_missing_flag():
    """不存在的 flag 返回 False"""
    assert FeatureFlags.is_enabled("flag_missing") is False


def test_role_grayscale():
    """角色灰度：仅 admin 角色可见"""
    assert FeatureFlags.is_enabled("flag_role", role_codes=["admin"]) is True
    assert FeatureFlags.is_enabled("flag_role", role_codes=["teacher"]) is False


def test_user_whitelist():
    """用户白名单"""
    assert FeatureFlags.is_enabled("flag_users", user_id=1) is True
    assert FeatureFlags.is_enabled("flag_users", user_id=99) is False


def test_school_grayscale():
    """校区灰度"""
    assert FeatureFlags.is_enabled("flag_school", school_id=1) is True
    assert FeatureFlags.is_enabled("flag_school", school_id=2) is False


def test_percentage_grayscale_consistent():
    """百分比灰度：同一用户结果一致"""
    r1 = FeatureFlags.is_enabled("flag_percent", user_id=42)
    r2 = FeatureFlags.is_enabled("flag_percent", user_id=42)
    assert r1 == r2


def test_percentage_all_users_possible():
    """百分比灰度：不同用户可能有不同结果"""
    results = {FeatureFlags.is_enabled("flag_percent", user_id=i) for i in range(1, 100)}
    # 50% 灰度下，应同时出现 True 和 False
    assert True in results and False in results


def test_hot_reload(tmp_path):
    """修改配置文件后热加载生效"""
    # 修改配置：关闭 flag_on
    path = tmp_path / "features.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["flag_on"]["enabled"] = False
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    # 不手动 reload，利用 mtime 变化自动重载
    assert FeatureFlags.is_enabled("flag_on") is False


def test_decorator_enabled():
    """feature_flag 装饰器：启用时正常执行"""

    @feature_flag("flag_on")
    def func():
        return "executed"

    assert func() == "executed"


def test_decorator_disabled_raises():
    """feature_flag 装饰器：禁用时抛 404"""

    @feature_flag("flag_off")
    def func():
        return "executed"

    with pytest.raises(Exception):
        func()


def test_decorator_disabled_returns_none():
    """feature_flag 装饰器：raise_on_disabled=False 返回 None"""

    @feature_flag("flag_off", raise_on_disabled=False)
    def func():
        return "executed"

    assert func() is None


def test_list_all():
    """列出所有 flags"""
    flags = FeatureFlags.list_all()
    assert "flag_on" in flags
    assert "flag_off" in flags
