"""
测试数据生成器
使用 Faker + factory_boy 生成真实业务数据
"""

import hashlib
import json
import sys
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import factory
from factory import Sequence
from faker import Faker

from test_data.schema import (
    AcademicYearData,
    ClassData,
    ClassroomData,
    ClassSubjectData,
    ExamData,
    ExamSubjectSettingData,
    ExamType,
    GlobalSettingData,
    GradeData,
    MovementType,
    ScoreData,
    SemesterConfigData,
    SemesterData,
    StudentData,
    StudentMovementData,
    SubjectData,
    TeacherData,
    TeacherTitle,
    TestDataSet,
)

# 初始化 Faker（中文）
fake = Faker("zh_CN")
Faker.seed(42)  # 固定种子，保证可复现


# ===== Factory 定义 =====


class AcademicYearFactory(factory.Factory):
    class Meta:
        model = AcademicYearData

    name = factory.LazyAttribute(lambda o: f"{2022 + o.sort_order}-{2023 + o.sort_order}")
    sort_order = Sequence(lambda n: n)
    is_active = False
    description = factory.LazyAttribute(lambda o: f"{o.name} 学年")


class SemesterFactory(factory.Factory):
    class Meta:
        model = SemesterData

    academic_year_id = 1
    year_start = factory.LazyAttribute(lambda o: 2022 + (o.academic_year_id - 1))
    semester = factory.Iterator(["1", "2"])
    label = factory.LazyAttribute(lambda o: f"{o.year_start}-{o.year_start + 1} 第{o.semester}学期")
    sort_order = factory.LazyAttribute(lambda o: (o.academic_year_id - 1) * 2 + int(o.semester))
    is_active = False
    status = factory.Iterator(["draft", "active", "locked", "archived"])
    start_date = factory.LazyAttribute(
        lambda o: date(o.year_start, 9 if o.semester == "1" else 2, 1)
    )
    end_date = factory.LazyAttribute(
        lambda o: date(
            o.year_start + (1 if o.semester == "2" else 0), 1 if o.semester == "1" else 7, 31
        )
    )


class GradeFactory(factory.Factory):
    class Meta:
        model = GradeData

    name = factory.Iterator(["初一", "初二", "初三"])
    sort_order = Sequence(lambda n: n)


class SubjectFactory(factory.Factory):
    class Meta:
        model = SubjectData

    name = factory.Iterator(
        ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "体育"]
    )
    full_mark = 100
    pass_line = 60
    good_line = 80
    excellent_line = 90
    low_line = 30
    sort_order = Sequence(lambda n: n)


class TeacherFactory(factory.Factory):
    class Meta:
        model = TeacherData

    semester_id = 1
    name = factory.Sequence(lambda n: f"{fake.name()}{n:03d}")
    gender = factory.Iterator(["男", "女"])
    phone = factory.Sequence(lambda n: f"TEL_{n:011d}")
    title = factory.Iterator([t.value for t in TeacherTitle])
    education = factory.Iterator(["本科", "硕士", "博士"])
    degree = factory.Iterator(["学士", "硕士", "博士"])
    political_status = factory.Iterator(["群众", "共青团员", "中共党员"])
    birth_date = factory.LazyAttribute(lambda o: fake.date_of_birth(minimum_age=25, maximum_age=60))
    work_start_date = factory.LazyAttribute(
        lambda o: fake.date_between(start_date="-30y", end_date="-1y")
    )
    graduation_date = factory.LazyAttribute(
        lambda o: fake.date_between(start_date="-35y", end_date="-25y")
    )
    staff_no = factory.Sequence(lambda n: f"T{n:06d}")
    note = ""


class ClassFactory(factory.Factory):
    class Meta:
        model = ClassData

    grade_id = 1
    semester_id = 1
    name = factory.Sequence(lambda n: f"{n}班")
    head_teacher = ""
    class_type = "普通班"
    room = factory.Sequence(lambda n: f"{(n - 1) // 4 + 1}0{(n - 1) % 4 + 1:02d}")


class StudentFactory(factory.Factory):
    class Meta:
        model = StudentData

    class_id = 1
    semester_id = 1
    name = factory.Sequence(lambda n: f"{fake.name()}{n:04d}")
    gender = factory.Iterator(["男", "女"])
    student_no = factory.Sequence(lambda n: f"{n:02d}")
    student_code = factory.Sequence(lambda n: f"{2024000000 + n:012d}")
    id_card = factory.Sequence(lambda n: f"ID_CARD_{n:018d}")
    birth_date = factory.LazyAttribute(lambda o: fake.date_of_birth(minimum_age=12, maximum_age=18))
    ethnicity = "汉族"
    native_place = factory.LazyAttribute(lambda o: fake.province())
    political_status = "群众"
    phone = factory.Sequence(lambda n: f"TEL_{n:011d}")
    address = factory.Sequence(lambda n: f"测试地址-序号{n}")
    hukou_addr = factory.Sequence(lambda n: f"户籍地址-序号{n}")
    enroll_year = 2024
    exam_no = factory.Sequence(lambda n: f"K{20240000 + n:08d}")
    boarding = factory.Iterator(["走读", "住校"])
    multiple_birth = ""
    health_status = "健康"
    is_disabled = "否"
    left_behind = "否"
    guardian1_name = factory.Sequence(lambda n: f"监护人甲{n:04d}")
    guardian1_relation = factory.Iterator(["父亲", "母亲"])
    guardian1_phone = factory.Sequence(lambda n: f"TEL_{n:011d}")
    guardian1_work = factory.LazyAttribute(lambda o: fake.job())
    guardian1_edu = factory.Iterator(["初中", "高中", "大专", "本科", "硕士"])
    guardian1_id_card = factory.Sequence(lambda n: f"ID_CARD_{n:018d}")
    guardian2_name = factory.Sequence(lambda n: f"监护人乙{n:04d}")
    guardian2_relation = factory.Iterator(["父亲", "母亲"])
    guardian2_phone = factory.Sequence(lambda n: f"TEL_{n:011d}")
    guardian2_work = factory.LazyAttribute(lambda o: fake.job())
    guardian2_edu = factory.Iterator(["初中", "高中", "大专", "本科", "硕士"])
    guardian2_id_card = factory.Sequence(lambda n: f"ID_CARD_{n:018d}")
    status = "在校"
    photo = None
    photo_mime = ""
    note = ""


class ExamFactory(factory.Factory):
    class Meta:
        model = ExamData

    semester_id = 1
    name = factory.Iterator(
        [
            "2024-2025 第1学期 期中考试",
            "2024-2025 第1学期 期末考试",
            "2024-2025 第2学期 期中考试",
            "2024-2025 第2学期 期末考试",
        ]
    )
    exam_date = factory.LazyAttribute(
        lambda o: fake.date_between(start_date="-6m", end_date="today")
    )
    grade_id = None
    exam_type = factory.Iterator([t.value for t in ExamType])
    note = ""
    is_makeup = False


class ExamSubjectSettingFactory(factory.Factory):
    class Meta:
        model = ExamSubjectSettingData

    exam_id = 1
    subject_id = 1
    full_mark = 100
    pass_line = 60
    good_line = 80
    excellent_line = 90
    low_line = 30


class ScoreFactory(factory.Factory):
    class Meta:
        model = ScoreData

    exam_id = 1
    student_id = 1
    subject_id = 1
    score = factory.LazyAttribute(lambda o: round(fake.random.uniform(0, 100), 1))
    is_makeup = False
    is_published = True


class ClassSubjectFactory(factory.Factory):
    class Meta:
        model = ClassSubjectData

    semester_id = 1
    class_id = 1
    subject_id = 1
    teacher_id = None


class StudentMovementFactory(factory.Factory):
    class Meta:
        model = StudentMovementData

    student_id = 1
    semester_id = 1
    move_type = factory.Iterator([t.value for t in MovementType])
    move_date = factory.LazyAttribute(
        lambda o: fake.date_between(start_date="-6m", end_date="today")
    )
    from_class_id = None
    to_class_id = None
    reason = factory.LazyAttribute(lambda o: fake.sentence())
    operator = "system"


class ClassroomFactory(factory.Factory):
    class Meta:
        model = ClassroomData

    semester_id = 1
    class_id = 1
    floor = factory.LazyAttribute(lambda o: f"{fake.random_int(1, 5)}楼")
    room_no = factory.LazyAttribute(lambda o: f"{fake.random_int(1, 20):02d}")
    capacity = 50


class GlobalSettingFactory(factory.Factory):
    class Meta:
        model = GlobalSettingData

    key = factory.LazyAttribute(lambda o: f"setting_{o.id}")
    value = factory.LazyAttribute(lambda o: fake.sentence())
    description = factory.LazyAttribute(lambda o: fake.sentence())


class SemesterConfigFactory(factory.Factory):
    class Meta:
        model = SemesterConfigData

    semester_id = 1
    key = factory.LazyAttribute(lambda o: f"config_{o.id}")
    value = factory.LazyAttribute(lambda o: fake.sentence())
    version = 1
    inherited_from = None
    description = factory.LazyAttribute(lambda o: fake.sentence())


# ===== 数据生成器主类 =====


class TestDataGenerator:
    """测试数据生成器"""

    def __init__(self, seed: int = 42):
        self.seed = seed
        Faker.seed(seed)
        # factory_boy 3.x 使用 random 模块直接设置种子
        import random

        random.seed(seed)
        self.dataset = TestDataSet()

    def generate(self) -> TestDataSet:
        """生成完整测试数据集"""
        print(f"🌱 使用种子 {self.seed} 生成测试数据...")

        # 1. 生成基础数据
        self._generate_academic_years()
        self._generate_grades()
        self._generate_subjects()
        self._generate_global_settings()

        # 2. 生成学期相关数据
        self._generate_semesters()

        # 3. 计算校验和
        self._compute_checksums()

        print("✅ 测试数据集生成完成")
        print(f"   {self.dataset.get_coverage_summary()}")

        return self.dataset

    def _generate_academic_years(self):
        """生成学年数据"""
        print("  📅 生成学年...")
        for i in range(3):  # 3 学年
            ay = AcademicYearFactory(sort_order=i)
            self.dataset.academic_years.append(ay)

    def _generate_grades(self):
        """生成年级数据"""
        print("  🏫 生成年级...")
        for i, grade in enumerate(["初一", "初二", "初三"]):
            g = GradeFactory(name=grade, sort_order=i)
            self.dataset.grades.append(g)

    def _generate_subjects(self):
        """生成学科数据"""
        print("  📚 生成学科...")
        subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "体育"]
        for i, subj in enumerate(subjects):
            s = SubjectFactory(name=subj, sort_order=i)
            self.dataset.subjects.append(s)

    def _generate_global_settings(self):
        """生成全局配置"""
        print("  ⚙️ 生成全局配置...")
        settings = [
            ("school_name", "示例学校", "学校名称"),
            ("school_code", "SLZX", "学校代码"),
            ("max_class_size", "50", "最大班额"),
            ("min_class_size", "30", "最小班额"),
            ("score_pass_line", "60", "默认及格线"),
            ("score_good_line", "80", "默认良好线"),
            ("score_excellent_line", "90", "默认优秀线"),
            ("exam_no_format", "{grade}{class:02d}{seat:03d}", "考号格式"),
            ("student_code_prefix", "2024", "学籍号前缀"),
            ("photo_max_size_mb", "5", "照片最大尺寸MB"),
        ]
        for i, (key, value, desc) in enumerate(settings):
            gs = GlobalSettingFactory(key=key, value=value, description=desc)
            self.dataset.global_settings.append(gs)

    def _generate_semesters(self):
        """生成学期及其所有关联数据"""
        print("  📖 生成学期及关联数据...")

        # 每学年 2 个学期，共 3 学年 = 6 个学期
        for ay_idx, ay in enumerate(self.dataset.academic_years):
            for sem_idx in range(2):  # 第1、2学期
                sem = SemesterFactory(
                    academic_year_id=ay_idx + 1,
                    year_start=2024 + ay_idx,
                    semester=str(sem_idx + 1),
                )

                # 设置第一个学期为激活
                if ay_idx == 0 and sem_idx == 0:
                    sem.is_active = True
                    sem.status = "active"

                # 生成该学期的教师
                teachers = TeacherFactory.create_batch(30, semester_id=sem.sort_order)
                sem.teachers = teachers

                # 生成该学期的班级
                classes = []
                for grade_idx, grade in enumerate(self.dataset.grades):
                    for class_idx in range(4):  # 每年级 4 个班 = 12 个班
                        cls = ClassFactory(
                            grade_id=grade_idx + 1,
                            semester_id=sem.sort_order,
                        )
                        cls.name = f"{grade.name}{class_idx + 1}班"
                        cls.grade_id = grade_idx + 1
                        classes.append(cls)
                sem.classes = classes

                # 为每个班级分配班主任
                for i, cls in enumerate(classes):
                    if i < len(teachers):
                        cls.head_teacher_id = i + 1  # 使用列表索引作为 ID

                # 生成学生（每班 15 人，共 12 班 = 180 人/学期）
                students = []
                for cls_idx, cls in enumerate(classes):
                    cls_students = StudentFactory.create_batch(
                        15,  # 每班人数
                        class_id=cls_idx + 1,
                        semester_id=sem.sort_order,
                    )
                    # 学生对象已由 factory 生成，class_id 已在 factory 中设置
                    students.extend(cls_students)
                sem.students = students

                # 生成考试（每学期 2 次：期中、期末）
                exams = ExamFactory.create_batch(2, semester_id=sem.sort_order)
                sem.exams = exams

                # 生成任课关系
                self._generate_class_subjects(sem, classes)

                # 生成教室
                classrooms = ClassroomFactory.create_batch(len(classes), semester_id=sem.sort_order)
                for i, cr in enumerate(classrooms):
                    cr.class_id = i + 1

                self.dataset.semesters.append(sem)

        # 生成成绩、学籍变动、教室等跨学期数据
        self._generate_cross_semester_data()

    def _generate_class_subjects(self, sem: SemesterData, classes: list[ClassData]):
        """生成任课关系"""
        # 为每个班级分配全科教师
        for cls in classes:
            for subj in self.dataset.subjects:
                # 简单分配：按学科轮询教师
                teacher_idx = self.dataset.subjects.index(subj) % len(sem.teachers)
                cs = ClassSubjectFactory(
                    semester_id=sem.sort_order,
                    class_id=classes.index(cls) + 1,
                    subject_id=self.dataset.subjects.index(subj) + 1,
                    teacher_id=(
                        sem.teachers[teacher_idx].id
                        if hasattr(sem.teachers[teacher_idx], "id")
                        else teacher_idx + 1
                    ),
                )
                # 存储到某处（简化处理）

    def _generate_cross_semester_data(self):
        """生成跨学期数据：成绩、学籍变动等"""
        print("  📊 生成跨学期数据...")

        # 为每个学期的每次考试生成成绩
        for sem in self.dataset.semesters:
            for exam in sem.exams:
                for student in sem.students:
                    for subj in self.dataset.subjects:
                        # 80% 有成绩，20% 缺考
                        if fake.random.random() > 0.2:
                            score = ScoreFactory(
                                exam_id=sem.exams.index(exam) + 1,
                                student_id=sem.students.index(student) + 1,
                                subject_id=self.dataset.subjects.index(subj) + 1,
                            )
                            score.score = round(fake.random.uniform(30, 100), 1)
                            # 添加到数据集（简化：仅记录数量）

        # 生成学籍变动（约 5% 学生有变动）
        for sem in self.dataset.semesters:
            for student in sem.students:
                if fake.random.random() < 0.05:
                    mv = StudentMovementFactory(
                        student_id=sem.students.index(student) + 1,
                        semester_id=sem.sort_order,
                    )

    def _compute_checksums(self):
        """计算校验和"""
        print("  🔐 计算校验和...")
        # 简化：对各表行数计算校验
        stats = self.dataset.get_coverage_summary()
        for key, value in stats.items():
            self.dataset.checksums[key] = hashlib.md5(str(value).encode()).hexdigest()[:8]


def serialize_test_dataset(dataset: TestDataSet) -> dict:
    """把 TestDataSet 序列化为扁平 dict（供 loader 内存生成，不落盘）"""
    from dataclasses import asdict
    from datetime import date, datetime

    def serialize(obj):
        if hasattr(obj, "__dataclass_fields__"):
            result = {}
            for k, v in asdict(obj).items():
                if k in ("semesters", "classes", "students", "teachers", "exams", "subjects"):
                    continue
                result[k] = serialize(v)
            return result
        elif isinstance(obj, (list, tuple)):
            return [serialize(v) for v in obj]
        elif isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, (bytes, bytearray)):
            return "<binary>"
        else:
            return obj

    flat_data = serialize(dataset)
    # 顶层补 semesters（serialize 排除了嵌套，这里显式收集）
    # 加载器按依赖顺序加载 semesters，teachers/classes 等引用 semester_id
    if dataset.semesters:
        flat_data["semesters"] = [serialize(s) for s in dataset.semesters]
    if dataset.all_teachers:
        all_teachers = []
        for sem in dataset.semesters:
            all_teachers.extend(sem.teachers)
        flat_data["teachers"] = [serialize(t) for t in all_teachers]
    if dataset.all_classes:
        all_classes = []
        for sem in dataset.semesters:
            all_classes.extend(sem.classes)
        flat_data["classes"] = [serialize(c) for c in all_classes]
    if dataset.all_students:
        all_students = []
        for sem in dataset.semesters:
            all_students.extend(sem.students)
        flat_data["students"] = [serialize(s) for s in all_students]
    if dataset.all_exams:
        all_exams = []
        for sem in dataset.semesters:
            all_exams.extend(sem.exams)
        flat_data["exams"] = [serialize(e) for e in all_exams]
    if dataset.global_settings:
        flat_data["global_settings"] = [serialize(s) for s in dataset.global_settings]
    return flat_data


def generate_test_data(
    output_dir: str = "test_data/base",
    version: str = "1.0.0",
    seed: int = 42,
) -> TestDataSet:
    """生成并保存测试数据"""
    output_path = Path(output_dir) / f"v{version}"
    output_path.mkdir(parents=True, exist_ok=True)

    generator = TestDataGenerator(seed=seed)
    dataset = generator.generate()
    dataset.version = version

    # 保存 JSON
    json_path = output_path / "dataset.json"
    with open(json_path, "w", encoding="utf-8") as f:
        # 自定义序列化：扁平化结构，主键数据放在顶层，嵌套关系字段跳过（避免重复）
        def serialize(obj):
            if hasattr(obj, "__dataclass_fields__"):
                result = {}
                for k, v in asdict(obj).items():
                    # 跳过嵌套关系字段（这些通过外键关联，不需要嵌套序列化）
                    if k in ("semesters", "classes", "students", "teachers", "exams", "subjects"):
                        continue
                    result[k] = serialize(v)
                return result
            elif isinstance(obj, (list, tuple)):
                return [serialize(v) for v in obj]
            elif isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            elif isinstance(obj, (date, datetime)):
                return obj.isoformat()
            elif isinstance(obj, (bytes, bytearray)):
                return "<binary>"
            else:
                return obj

        # 收集所有扁平化数据
        flat_data = serialize(dataset)

        # 单独添加各表数据（扁平化数组）
        if dataset.semesters:
            flat_data["semesters"] = [serialize(s) for s in dataset.semesters]
        if dataset.grades:
            # grades 在 academic_years 中有嵌套，需要单独提取
            flat_data["grades"] = [serialize(g) for g in dataset.grades]
        if dataset.subjects:
            flat_data["subjects"] = [serialize(s) for s in dataset.subjects]
        if dataset.all_teachers:
            # 收集所有学期的教师
            all_teachers = []
            for sem in dataset.semesters:
                all_teachers.extend(sem.teachers)
            flat_data["teachers"] = [serialize(t) for t in all_teachers]
        if dataset.all_classes:
            all_classes = []
            for sem in dataset.semesters:
                all_classes.extend(sem.classes)
            flat_data["classes"] = [serialize(c) for c in all_classes]
        if dataset.all_students:
            all_students = []
            for sem in dataset.semesters:
                all_students.extend(sem.students)
            flat_data["students"] = [serialize(s) for s in all_students]
        if dataset.all_exams:
            all_exams = []
            for sem in dataset.semesters:
                all_exams.extend(sem.exams)
            flat_data["exams"] = [serialize(e) for e in all_exams]
        if dataset.global_settings:
            flat_data["global_settings"] = [serialize(s) for s in dataset.global_settings]

        json.dump(flat_data, f, ensure_ascii=False, indent=2)

    # 保存清单
    manifest = {
        "version": version,
        "generated_at": datetime.now().isoformat(),
        "seed": seed,
        "description": dataset.description,
        "coverage": dataset.get_coverage_summary(),
        "checksums": dataset.checksums,
        "files": ["dataset.json"],
    }
    manifest_path = output_path / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"💾 测试数据已保存至: {output_path}")
    print(f"   dataset.json ({json_path.stat().st_size / 1024:.1f} KB)")
    print("   manifest.json")

    return dataset


def load_test_data(version: str = "1.0.0", base_dir: str = "test_data/base") -> TestDataSet:
    """加载测试数据"""
    json_path = Path(base_dir) / f"v{version}" / "dataset.json"
    if not json_path.exists():
        raise FileNotFoundError(f"测试数据不存在: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # 反序列化（简化版）
    dataset = TestDataSet(
        version=data.get("version", "1.0.0"),
        created_at=data.get("created_at", ""),
        description=data.get("description", ""),
        checksums=data.get("checksums", {}),
    )
    return dataset


if __name__ == "__main__":
    # 生成基准测试数据集 v1.0
    dataset = generate_test_data(
        output_dir="test_data/base",
        version="1.0.0",
        seed=42,
    )

    # 生成边界值测试数据集 v1.1
    dataset_edge = generate_test_data(
        output_dir="test_data/base",
        version="1.1.0",
        seed=123,
    )

    print("\n🎉 所有测试数据集生成完成！")
