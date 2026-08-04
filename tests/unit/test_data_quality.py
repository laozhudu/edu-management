"""
数据质量服务单元测试
验证：合法数据通过、非法数据报错、画像、业务规则、不同实体
"""

from edu_system.services.data_quality import data_quality_service

VALID_STUDENTS = [
    {
        "学号": "2024001",
        "姓名": "张三",
        "性别": "男",
        "年级": "初三",
        "班级": "1班",
        "联系电话": "13800138000",
    },
    {
        "学号": "2024002",
        "姓名": "李四",
        "性别": "女",
        "年级": "初三",
        "班级": "1班",
        "联系电话": "13900139000",
    },
]

VALID_SCORES = [
    {"考试": "期中", "学号": "2024001", "科目": "语文", "成绩": 92.5},
    {"考试": "期中", "学号": "2024002", "科目": "语文", "成绩": 85.0},
]


class TestDataQuality:
    def test_valid_students_pass(self):
        """合法学生数据通过验证"""
        report = data_quality_service.validate("student", VALID_STUDENTS)
        assert report.passed is True
        assert report.error_count == 0
        assert report.total_rows == 2

    def test_invalid_phone(self):
        """非法手机号报错"""
        data = [
            {
                "学号": "2024001",
                "姓名": "张三",
                "性别": "男",
                "年级": "初三",
                "班级": "1班",
                "联系电话": "123",
            }
        ]
        report = data_quality_service.validate("student", data)
        assert report.passed is False
        assert report.error_count >= 1
        assert any(i.column == "联系电话" for i in report.issues)

    def test_duplicate_student_id(self):
        """学号重复报错"""
        data = VALID_STUDENTS + [dict(VALID_STUDENTS[0])]
        report = data_quality_service.validate("student", data)
        assert report.passed is False
        assert any("学号" in i.column for i in report.issues)

    def test_score_out_of_range(self):
        """成绩超出范围报错"""
        data = [{"考试": "期中", "学号": "2024001", "科目": "语文", "成绩": 999}]
        report = data_quality_service.validate("score", data)
        assert report.passed is False

    def test_score_duplicate_warning(self):
        """成绩重复记录产生 warning"""
        data = VALID_SCORES + [dict(VALID_SCORES[0])]
        report = data_quality_service.validate("score", data)
        assert any(i.severity == "warning" for i in report.issues)

    def test_valid_score_pass(self):
        """合法成绩通过"""
        report = data_quality_service.validate("score", VALID_SCORES)
        assert report.passed is True

    def test_unknown_entity(self):
        """未知实体类型报错"""
        report = data_quality_service.validate("unknown_entity", VALID_STUDENTS)
        assert report.passed is False
        assert "未知实体" in report.issues[0].message

    def test_empty_data_passes(self):
        """空数据通过（无错误）"""
        report = data_quality_service.validate("student", [])
        assert report.passed is True

    def test_column_profile(self):
        """列画像包含统计信息"""
        report = data_quality_service.validate("student", VALID_STUDENTS)
        assert "姓名" in report.column_profiles
        profile = report.column_profiles["姓名"]
        assert "non_null" in profile
        assert "unique_count" in profile

    def test_numeric_profile(self):
        """数值列画像含 min/max"""
        report = data_quality_service.validate("score", VALID_SCORES)
        profile = report.column_profiles["成绩"]
        assert profile["min"] == 85.0
        assert profile["max"] == 92.5

    def test_summary_dict(self):
        """summary 返回 API 友好 dict"""
        report = data_quality_service.validate("student", VALID_STUDENTS)
        s = report.summary()
        assert s["entity"] == "student"
        assert s["total_rows"] == 2
        assert s["passed"] is True

    def test_teacher_valid(self):
        """合法教师数据通过"""
        data = [{"工号": "1001", "姓名": "王老师", "科目": "语文", "邮箱": "wang@school.com"}]
        report = data_quality_service.validate("teacher", data)
        assert report.passed is True

    def test_teacher_invalid_email(self):
        """教师非法邮箱报错"""
        data = [{"工号": "1001", "姓名": "王老师", "性别": "男", "邮箱": "invalid-email"}]
        report = data_quality_service.validate("teacher", data)
        assert report.passed is False

    def test_student_missing_phone_warning(self):
        """学生缺手机号产生 warning"""
        data = [{"学号": "2024001", "姓名": "张三", "性别": "男", "年级": "初三", "班级": "1班"}]
        report = data_quality_service.validate("student", data)
        assert any(i.severity == "warning" and i.column == "联系电话" for i in report.issues)
