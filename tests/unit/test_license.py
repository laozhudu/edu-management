"""
授权许可服务单测（M6 Sprint 7）

覆盖：
- 授权码生成/校验（格式/签名/机器绑定）
- 激活流程（成功/失败）
- 状态查询（未激活/已激活/过期）
- 许可校验（宽松模式/强制模式）
"""

from datetime import datetime, timedelta

import pytest

from edu_system.services.license import (
    KEY_ACTIVATED,
    KEY_CODE,
    KEY_EXPIRES,
    KEY_MACHINE_ID,
    LicenseService,
    generate_license_code,
    get_machine_id,
    verify_license_code,
)


@pytest.fixture
def session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


class TestLicenseCode:
    def test_generate_and_verify_ok(self):
        """生成→校验通过，days 正确"""
        code = generate_license_code(days=100)
        result = verify_license_code(code)
        assert result["valid"] is True
        assert result["days"] == 100

    def test_verify_wrong_format(self):
        """格式错误拒绝"""
        result = verify_license_code("abc")
        assert result["valid"] is False
        assert "格式" in result["reason"]

    def test_verify_machine_mismatch(self):
        """机器绑定：伪造其他机器 ID 拒绝"""
        fake_mid = "f" * 24
        code = generate_license_code(machine_id=fake_mid, days=30)
        # 当前机器 ID 与 fake_mid 不同 → 拒绝
        result = verify_license_code(code)
        assert result["valid"] is False
        assert "不匹配" in result["reason"]

    def test_verify_tampered_signature(self):
        """篡改天数后签名无效拒绝"""
        code = generate_license_code(days=30)
        parts = code.split(".")
        tampered = f"{parts[0]}.999.{parts[2]}"
        result = verify_license_code(tampered)
        assert result["valid"] is False


class TestLicenseService:
    def test_activate_success(self, session):
        """激活成功：settings 写入激活状态"""
        code = generate_license_code(days=90)
        svc = LicenseService(session)
        result = svc.activate(code)
        assert result["success"] is True

        status = svc.get_status()
        assert status["activated"] is True
        assert status["days_left"] <= 90
        assert status["code"] == code

    def test_activate_invalid_code(self, session):
        """无效授权码激活失败"""
        svc = LicenseService(session)
        result = svc.activate("invalid.code.here")
        assert result["success"] is False

    def test_status_not_activated(self, session):
        """未激活状态"""
        svc = LicenseService(session)
        status = svc.get_status()
        assert status["activated"] is False

    def test_check_license_loose_mode(self, session, monkeypatch):
        """宽松模式：未激活也允许（EDU_LICENSE_REQUIRED 未设置）"""
        monkeypatch.delenv("EDU_LICENSE_REQUIRED", raising=False)
        svc = LicenseService(session)
        result = svc.check_license(required=False)
        assert result["allowed"] is True
        assert "宽松" in result["reason"]

    def test_check_license_hard_mode(self, session, monkeypatch):
        """强制模式：未激活拒绝"""
        monkeypatch.setenv("EDU_LICENSE_REQUIRED", "1")
        svc = LicenseService(session)
        result = svc.check_license(required=True)
        assert result["allowed"] is False

    def test_check_license_expired(self, session):
        """许可过期拒绝"""
        from edu_system.models import Setting

        session.add(Setting(key=KEY_ACTIVATED, value="1"))
        session.add(Setting(key=KEY_CODE, value="test-code"))
        session.add(
            Setting(
                key=KEY_EXPIRES,
                value=(datetime.now() - timedelta(days=1)).isoformat(),
            )
        )
        session.add(Setting(key=KEY_MACHINE_ID, value=get_machine_id()))
        session.commit()

        svc = LicenseService(session)
        result = svc.check_license(required=True)
        assert result["allowed"] is False
        assert "过期" in result["reason"]
