"""
数据清洗管道单元测试
验证：列名标准化、去空格、缺失填补、性别标准化、手机号校验、去重、单值工具
"""

import pandas as pd

from edu_system.services.data_cleaning import (
    CleaningConfig,
    DataCleaningPipeline,
    normalize_phone,
    standardize_gender,
)


class TestDataCleaning:
    def test_column_normalize(self):
        """列名去空格"""
        df = pd.DataFrame({" 学号 ": [1], "姓名": ["张三"]})
        result = DataCleaningPipeline().run(df)
        assert "学号" in result.cleaned.columns
        assert " 学号 " not in result.cleaned.columns

    def test_strip_text(self):
        """字符串去首尾空格"""
        df = pd.DataFrame({"姓名": [" 张三 ", "李四"]})
        config = CleaningConfig(strip_columns=["姓名"])
        result = DataCleaningPipeline(config).run(df)
        assert result.cleaned["姓名"].tolist() == ["张三", "李四"]

    def test_fill_missing(self):
        """缺失值填补"""
        df = pd.DataFrame({"年级": ["初一", None, "初二"]})
        config = CleaningConfig(fill_missing={"年级": "未知"})
        result = DataCleaningPipeline(config).run(df)
        assert result.filled_cells == 1
        assert result.cleaned["年级"].tolist() == ["初一", "未知", "初二"]

    def test_gender_normalize(self):
        """性别标准化（m/f/male 映射）"""
        df = pd.DataFrame({"性别": ["男", "m", "female", "女"]})
        config = CleaningConfig(normalize_gender=True)
        result = DataCleaningPipeline(config).run(df)
        assert result.cleaned["性别"].tolist() == ["男", "男", "女", "女"]

    def test_phone_validation(self):
        """手机号校验产生 issues"""
        df = pd.DataFrame({"联系电话": ["13800138000", "123", "13900139000"]})
        config = CleaningConfig(phone_columns=["联系电话"])
        result = DataCleaningPipeline(config).run(df)
        assert any(i["column"] == "联系电话" for i in result.issues)
        assert len(result.cleaned) == 3  # 非法行保留

    def test_dedup(self):
        """按学号去重"""
        df = pd.DataFrame(
            {"学号": ["2024001", "2024002", "2024001"], "姓名": ["张三", "李四", "张三重复"]}
        )
        config = CleaningConfig(dedup_keys=["学号"])
        result = DataCleaningPipeline(config).run(df)
        assert result.dropped_rows == 1
        assert len(result.cleaned) == 2
        assert result.cleaned["学号"].tolist() == ["2024001", "2024002"]

    def test_dedup_keep_first(self):
        """去重保留首行"""
        df = pd.DataFrame({"学号": ["2024001", "2024001"], "姓名": ["张三", "张三重复"]})
        config = CleaningConfig(dedup_keys=["学号"])
        result = DataCleaningPipeline(config).run(df)
        assert result.cleaned["姓名"].tolist() == ["张三"]

    def test_no_dedup_keys(self):
        """未配置去重键则不去重"""
        df = pd.DataFrame({"学号": ["2024001", "2024001"]})
        result = DataCleaningPipeline().run(df)
        assert len(result.cleaned) == 2

    def test_summary(self):
        """summary 摘要"""
        df = pd.DataFrame({"学号": ["2024001", "2024001"]})
        config = CleaningConfig(dedup_keys=["学号"])
        result = DataCleaningPipeline(config).run(df)
        s = result.summary()
        assert s["dropped_rows"] == 1
        assert s["rows_after"] == 1

    def test_standardize_gender_single(self):
        """单值性别标准化"""
        assert standardize_gender("M") == "男"
        assert standardize_gender("female") == "女"
        assert standardize_gender(None) == ""

    def test_normalize_phone_single(self):
        """单值手机号标准化"""
        assert normalize_phone("138 0013 8000") == "13800138000"
        assert normalize_phone("139-0013-9000") == "13900139000"
        assert normalize_phone("abc") is None
        assert normalize_phone(None) is None
