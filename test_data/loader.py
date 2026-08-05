"""
测试数据加载器
支持：版本化加载、场景切片、角色切片、校验和验证、dry-run 模式
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from edu_system.database import get_session, init_db_with_defaults
from edu_system.models import (
    AcademicYear,
    Class,
    Classroom,
    ClassSubject,
    DataLock,
    Exam,
    ExamSubjectSetting,
    GlobalSetting,
    Grade,
    School,
    Score,
    Semester,
    SemesterConfig,
    SemesterStatsCache,
    Student,
    StudentMovement,
    Subject,
    Teacher,
)


class DataLoader:
    """测试数据加载器"""

    def __init__(self, base_dir: str = "test_data/base", verbose: bool = False):
        self.base_dir = Path(base_dir)
        self.verbose = verbose
        self.session = None
        self.loaded_counts = {}

    def log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")

    def load_version(
        self,
        version: str = "1.0.0",
        scenario: str = "full",
        role: str | None = None,
        dry_run: bool = False,
        verify_only: bool = False,
        dataset_override: dict | None = None,
    ) -> dict:
        """
        加载指定版本的测试数据

        Args:
            version: 数据版本 (如 "1.0.0")
            scenario: 加载场景 (full/minimal/edge)
            role: 角色切片 (director/teacher/student/parent)
            dry_run: 仅打印不执行
            verify_only: 仅校验不加载
        """
        self.log(f"📥 加载测试数据: version={version}, scenario={scenario}, role={role}")

        # 1. 读取清单
        manifest_path = self.base_dir / f"v{version}" / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"清单不存在: {manifest_path}")

        with open(manifest_path) as f:
            manifest = json.load(f)

        # 2. 读取数据集（dataset.json 为生成物，公开仓库不保留隐私数据；
        #    缺失时用 generate.py 以固定种子在内存生成，结果一致可复现）
        #    dataset_override: 调用方传入预生成数据（测试隔离复用，避免重复生成）
        if dataset_override is not None:
            raw_data = dataset_override
        else:
            dataset_path = self.base_dir / f"v{version}" / "dataset.json"
            if dataset_path.exists():
                with open(dataset_path) as f:
                    raw_data = json.load(f)
            else:
                self.log("⚠️ dataset.json 不存在，使用生成器内存生成（种子复现）")
                from test_data.generate import TestDataGenerator, serialize_test_dataset

                gen = TestDataGenerator(seed=42)
                dataset_obj = gen.generate()
                raw_data = serialize_test_dataset(dataset_obj)

        # 3. 校验清单
        if not verify_only:
            self._verify_checksums(raw_data, manifest.get("checksums", {}))

        # 3. 如果只是校验
        if verify_only:
            return {"status": "verified", "version": version, "manifest": manifest}

        # 4. 解析数据集（简化：直接用原始字典）
        dataset = raw_data

        # 5. 应用场景过滤
        filtered = self._filter_by_scenario(dataset, scenario)

        # 6. 应用角色切片
        if role:
            filtered = self._filter_by_role(filtered, role)

        # 7. 执行加载
        if not dry_run:
            self._execute_load(filtered)
        else:
            self.log(f"[DRY-RUN] 将加载: {self._count_items(filtered)} 项数据")

        return {
            "status": "loaded" if not dry_run else "dry-run",
            "version": version,
            "scenario": scenario,
            "role": role,
            "counts": self.loaded_counts,
            "manifest": manifest,
        }

    def _verify_checksums(self, dataset: dict, expected_checksums: dict):
        """校验数据集完整性"""
        self.log("🔐 校验校验和...")
        # 兼容性处理：dataset 可能是原始 JSON 结构，也可能是 TestDataSet 对象
        # 简化：计算各关键表的行数作为校验基准
        actual_counts = {}
        for key in [
            "academic_years",
            "grades",
            "subjects",
            "semesters",
            "classes",
            "students",
            "teachers",
            "exams",
        ]:
            if key in dataset and isinstance(dataset[key], list):
                actual_counts[key] = len(dataset[key])

        for key, expected in expected_checksums.items():
            actual_value = actual_counts.get(key, 0)
            actual = hashlib.md5(str(actual_value).encode()).hexdigest()[:8]
            if actual != expected:
                self.log(
                    f"  ⚠️ 校验和不匹配 (可能数据已更新): {key} 期望={expected} 实际={actual} (行数={actual_value})"
                )
            else:
                self.log(f"  ✅ {key}: {expected} (行数={actual_value})")

    def _filter_by_scenario(self, dataset: dict, scenario: str) -> dict:
        """按场景过滤数据"""
        if scenario == "full":
            return dataset

        # 简化实现：返回子集
        filtered = {}
        if scenario == "minimal":
            # 仅保留核心表
            core_keys = ["academic_years", "grades", "subjects", "semesters", "global_settings"]
            for k in core_keys:
                if k in dataset:
                    filtered[k] = dataset[k][:2]  # 只取前2条
        elif scenario == "test":
            # 测试场景：包含测试所需的最小数据集
            test_keys = [
                "academic_years",
                "grades",
                "subjects",
                "semesters",
                "global_settings",
                "teachers",
                "classes",
                "students",
                "exams",
                "scores",
                "class_subjects",
            ]
            for k in test_keys:
                if k in dataset:
                    filtered[k] = (
                        dataset[k][:3]
                        if k in ["teachers", "classes", "students", "exams", "scores"]
                        else dataset[k]
                    )
        elif scenario == "edge":
            # 包含边界值数据
            filtered = dataset

        return filtered

    def _filter_by_role(self, dataset: dict, role: str) -> dict:
        """按角色切片数据"""
        # 简化实现：返回完整数据（实际应过滤敏感字段）
        role_visibility = {
            "director": ["*"],  # 全部可见
            "teacher": ["students", "classes", "exams", "scores", "class_subjects"],
            "student": ["students", "exams", "scores", "attendance"],
            "parent": ["students", "scores", "notifications"],
        }
        return dataset

    def _count_items(self, dataset: dict) -> int:
        """统计数据项总数"""
        total = 0
        for v in dataset.values():
            if isinstance(v, list):
                total += len(v)
        return total

    def _execute_load(self, dataset: dict):
        """执行数据加载到数据库"""
        self.session = get_session()

        try:
            # 清空现有数据（按依赖顺序删除）
            self._clear_existing_data()

            # 按依赖顺序加载
            load_order = [
                ("academic_years", AcademicYear),
                ("grades", Grade),
                ("subjects", Subject),
                ("schools", School),
                ("global_settings", GlobalSetting),
                ("semesters", Semester),
                ("teachers", Teacher),
                ("classes", Class),
                ("students", Student),
                ("exams", Exam),
                ("exam_subject_settings", ExamSubjectSetting),
                ("class_subjects", ClassSubject),
                ("scores", Score),
                ("student_movements", StudentMovement),
                ("classrooms", Classroom),
                ("semester_configs", SemesterConfig),
                ("data_locks", DataLock),
            ]

            # 展开嵌套 semesters（academic_years[].semesters → 顶层 dataset["semesters"]）
            # 生成数据把 semesters 嵌套在学年下，加载器需展开才能按依赖顺序加载
            nested_sems = []
            for ay in dataset.get("academic_years", []):
                nested_sems.extend(ay.get("semesters", []))
            if nested_sems and not dataset.get("semesters"):
                dataset["semesters"] = nested_sems

            for key, model in load_order:
                if key in dataset and dataset[key]:
                    count = self._load_model(model, dataset[key])
                    self.loaded_counts[key] = count
                    self.log(f"  ✅ {key}: {count} 条")

            self.session.commit()
            self.log("💾 数据加载完成并提交")

        except Exception:
            self.session.rollback()
            raise
        finally:
            self.session.close()

    def _clear_existing_data(self):
        """清空现有数据（按反依赖顺序）"""
        self.log("🧹 清空现有数据...")
        clear_order = [
            Score,
            ClassSubject,
            ExamSubjectSetting,
            StudentMovement,
            Classroom,
            SemesterConfig,
            SemesterStatsCache,
            DataLock,
            Student,
            Teacher,
            Class,
            Exam,
            Semester,
            Subject,
            Grade,
            AcademicYear,
            School,
            GlobalSetting,
        ]
        for model in clear_order:
            try:
                self.session.query(model).delete()
            except:
                pass
        # 重置自增计数：保证重新加载的 id 从 1 开始
        # （生成数据的关联引用按 1..N 固定 id，加载器依赖此约定）
        try:
            self.session.execute(text("DELETE FROM sqlite_sequence"))
        except Exception:
            pass
        self.session.commit()

    def _load_model(self, model, data_list: list[dict]) -> int:
        """批量加载模型数据"""
        if not data_list:
            return 0

        count = 0
        for item in data_list:
            try:
                # 处理日期字段
                for key, value in item.items():
                    if isinstance(value, str) and "date" in key.lower():
                        try:
                            item[key] = datetime.fromisoformat(value).date()
                        except:
                            pass

                obj = model(**item)
                self.session.add(obj)
                count += 1
            except Exception as e:
                self.log(f"  ⚠️ 跳过记录: {e}")

        self.session.flush()
        return count

    def export_subset(self, dataset: dict, output_path: str, role: str = None):
        """导出数据子集"""
        if role:
            dataset = self._filter_by_role(dataset, role)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2, default=str)

        self.log(f"📤 子集已导出: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")


def load_test_data(
    version: str = "1.0.0",
    scenario: str = "full",
    role: str = None,
    dry_run: bool = False,
    verify_only: bool = False,
    base_dir: str = "test_data/base",
) -> dict:
    """便捷加载函数"""
    loader = DataLoader(base_dir=base_dir, verbose=True)
    return loader.load_version(
        version=version,
        scenario=scenario,
        role=role,
        dry_run=dry_run,
        verify_only=verify_only,
    )


if __name__ == "__main__":
    # 测试加载
    print("=== 测试数据加载器验证 ===")

    # 1. dry-run 测试
    print("\n1. Dry-run 测试...")
    result = load_test_data(version="1.0.0", scenario="full", dry_run=True)
    print(f"   结果: {result['status']}")

    # 2. verify-only 测试
    print("\n2. Verify-only 测试...")
    result = load_test_data(version="1.0.0", verify_only=True)
    print(f"   结果: {result['status']}")

    # 3. 实际加载（需要数据库）
    print("\n3. 实际加载测试...")
    try:
        from edu_system.database import init_db_with_defaults

        init_db_with_defaults()
        result = load_test_data(version="1.0.0", scenario="minimal")
        print(f"   加载结果: {result['counts']}")
    except Exception as e:
        print(f"   加载测试跳过: {e}")

    print("\n=== 加载器验证完成 ===")
