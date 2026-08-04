"""FieldService 单元测试 — 动态字段增删（Sprint 3.7 核心）"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from edu_system.services.meta import FieldService, FieldValidationError


@pytest.fixture
def session():
    """内存 SQLite 会话（含 field_definitions + students 表）"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from edu_system.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


@pytest.fixture
def svc(session):
    return FieldService(session)


# ── 字段定义 CRUD ──
def test_add_and_list_field(svc):
    svc.add_field("student", "height_cm", "身高(cm)", field_type="float", sort_order=10)
    fields = svc.list_fields("student")
    assert len(fields) == 1
    assert fields[0].field_key == "height_cm"
    assert fields[0].label == "身高(cm)"
    assert fields[0].field_type == "float"
    assert fields[0].is_system is False


def test_add_duplicate_field_rejected(svc):
    svc.add_field("student", "height_cm", "身高")
    with pytest.raises(FieldValidationError, match="已存在"):
        svc.add_field("student", "height_cm", "重复")


def test_invalid_entity_rejected(svc):
    with pytest.raises(FieldValidationError, match="实体类型"):
        svc.add_field("alien", "x", "X")


def test_invalid_field_type_rejected(svc):
    with pytest.raises(FieldValidationError, match="字段类型"):
        svc.add_field("student", "x", "X", field_type="blob")


def test_enum_requires_options(svc):
    with pytest.raises(FieldValidationError, match="options"):
        svc.add_field("student", "blood", "血型", field_type="enum")


def test_update_field(svc):
    svc.add_field("student", "height_cm", "身高")
    svc.update_field("student", "height_cm", label="身高(cm)", sort_order=5)
    fd = svc.get_field("student", "height_cm")
    assert fd.label == "身高(cm)"
    assert fd.sort_order == 5


def test_delete_field(svc):
    svc.add_field("student", "temp", "临时")
    assert svc.delete_field("student", "temp") is True
    assert svc.get_field("student", "temp") is None


def test_delete_system_field_rejected(svc):
    """系统字段不可删除"""

    svc.add_field("student", "sys_field", "系统字段")
    fd = svc.get_field("student", "sys_field")
    fd.is_system = True
    svc._session.commit()
    with pytest.raises(FieldValidationError, match="系统字段"):
        svc.delete_field("student", "sys_field")


# ── ext_json 读写 ──
def test_set_and_get_ext_value(svc, session):
    from edu_system.models import Class, Grade, Student

    # 建最小数据链
    g = Grade(name="高一", sort_order=1)
    session.add(g)
    session.flush()
    c = Class(grade_id=g.id, semester_id=1, name="1班")
    session.add(c)
    session.flush()
    s = Student(class_id=c.id, name="张三", semester_id=1, status="在校")
    session.add(s)
    session.commit()

    # 写自定义字段
    FieldService.set_value(s, "height_cm", 175.5)
    FieldService.set_value(s, "blood_type", "A")
    session.commit()

    # 读回（保留多字段）
    assert FieldService.get_value(s, "height_cm") == 175.5
    assert FieldService.get_value(s, "blood_type") == "A"
    # 未定义字段返回默认
    assert FieldService.get_value(s, "nope", "缺省") == "缺省"


def test_set_value_preserves_other_keys(svc, session):
    from edu_system.models import Class, Grade, Student

    g = Grade(name="高一", sort_order=1)
    session.add(g)
    session.flush()
    c = Class(grade_id=g.id, semester_id=1, name="1班")
    session.add(c)
    session.flush()
    s = Student(class_id=c.id, name="李四", semester_id=1, status="在校")
    session.add(s)
    session.commit()

    FieldService.set_value(s, "a", 1)
    FieldService.set_value(s, "b", 2)
    session.commit()
    assert FieldService.get_value(s, "a") == 1
    assert FieldService.get_value(s, "b") == 2


# ── 值校验 ──
def test_validate_required(svc):
    svc.add_field("student", "must", "必填", required=True)
    with pytest.raises(FieldValidationError, match="必填"):
        svc.validate_value("student", "must", None)


def test_validate_int(svc):
    svc.add_field("student", "age", "年龄", field_type="int")
    assert svc.validate_value("student", "age", "18") == 18
    with pytest.raises(FieldValidationError, match="格式错误"):
        svc.validate_value("student", "age", "abc")


def test_validate_enum_options(svc):
    svc.add_field("student", "blood", "血型", field_type="enum", options=["A", "B", "O"])
    assert svc.validate_value("student", "blood", "A") == "A"
    with pytest.raises(FieldValidationError, match="非法选项"):
        svc.validate_value("student", "blood", "Z")


def test_validate_undefined_field(svc):
    with pytest.raises(FieldValidationError, match="未定义"):
        svc.validate_value("student", "ghost", "x")


# ── 按自定义字段查询（3.7.12）──
def test_query_by_field_matches_value(svc):
    from edu_system.models import Student

    svc.add_field("student", "hobby", "兴趣爱好")
    # 造两个学生，写入不同 hobby
    s1 = Student(name="张三", class_id=0, semester_id=0)
    s2 = Student(name="李四", class_id=0, semester_id=0)
    svc._session.add_all([s1, s2])
    svc._session.commit()
    FieldService.set_value(s1, "hobby", "篮球")
    FieldService.set_value(s2, "hobby", "足球")
    svc._session.commit()

    results = svc.query_by_field("student", "hobby", "篮球")
    assert len(results) == 1
    assert results[0].name == "张三"


def test_query_by_field_no_match(svc):
    from edu_system.models import Student

    svc.add_field("student", "hobby", "兴趣爱好")
    s = Student(name="张三", class_id=0, semester_id=0)
    svc._session.add(s)
    svc._session.commit()
    FieldService.set_value(s, "hobby", "篮球")
    svc._session.commit()

    assert svc.query_by_field("student", "hobby", "不存在的值") == []


def test_query_by_field_undefined_rejected(svc):
    with pytest.raises(FieldValidationError, match="未定义"):
        svc.query_by_field("student", "ghost", "x")
