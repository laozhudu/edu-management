#!/usr/bin/env python3
"""
内存缓存层 — 静态/半静态数据全量内存化，查询零 SQL
适用场景：学期制教务系统，学期内数据基本只读
"""

from collections import defaultdict
from threading import Lock

from sqlalchemy.orm import Session


class MemoryCache:
    """单例内存缓存：启动时全量加载，查询走内存"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # 基础静态数据（按学期/年级分区）
        self.grades = {}  # id -> Grade
        self.grades_by_name = {}  # name -> Grade
        self.classes = {}  # id -> Class
        self.classes_by_grade = defaultdict(list)  # grade_id -> [Class]
        self.subjects = {}  # id -> Subject
        self.subjects_by_grade = defaultdict(list)  # grade_name -> [Subject]
        self.teachers = {}  # id -> Teacher
        self.semesters = {}  # id -> Semester
        self.current_semester = None

        # 学生数据（内存模式：全量加载，按班级/状态索引）
        self.students = {}  # id -> Student
        self.students_by_class = defaultdict(list)  # class_id -> [Student]
        self.students_by_grade = defaultdict(list)  # grade_id -> [Student]
        self.students_in_school = []  # 所有在校生

        # 考试/成绩（按需加载，考试级缓存）
        self.exams = {}  # id -> Exam
        self.exams_by_grade = defaultdict(list)
        self.scores_cache = {}  # exam_id -> {student_id: {subject: score}}

    def load_all(self, session: Session):
        """启动时一次性加载所有静态/半静态数据"""
        from src.edu_system.models import Class, Exam, Grade, Semester, Student, Subject, Teacher

        # 1. 年级
        for g in session.query(Grade).order_by(Grade.sort_order).all():
            self.grades[g.id] = g
            self.grades_by_name[g.name] = g

        # 2. 班级
        for c in session.query(Class).all():
            self.classes[c.id] = c
            self.classes_by_grade[c.grade_id].append(c)

        # 3. 学科
        for s in session.query(Subject).order_by(Subject.sort_order).all():
            self.subjects[s.id] = s
            # 学科归属年级：通过 sort_order 推断或显式字段
            # 简化：全学科对所有年级可见，后续按需过滤

        # 4. 教师
        for t in session.query(Teacher).all():
            self.teachers[t.id] = t

        # 5. 学期
        for s in session.query(Semester).all():
            self.semesters[s.id] = s
            if s.is_active:
                self.current_semester = s

        # 6. 学生（全量内存化，按班级/年级建索引）
        students = session.query(Student).filter(Student.status == "在校").all()
        for stu in students:
            self.students[stu.id] = stu
            if stu.class_id:
                self.students_by_class[stu.class_id].append(stu)
            if stu.class_id and stu.class_id in self.classes:
                cls = self.classes[stu.class_id]
                self.students_by_grade[cls.grade_id].append(stu)
        self.students_in_school = students

        # 7. 考试
        for e in session.query(Exam).all():
            self.exams[e.id] = e
            if e.grade_id:
                self.exams_by_grade[e.grade_id].append(e)

        print(
            f"[Cache] Loaded: {len(self.grades)} grades, {len(self.classes)} classes, "
            f"{len(self.subjects)} subjects, {len(self.teachers)} teachers, "
            f"{len(students)} students, {len(self.exams)} exams"
        )

    # ===== 查询接口（全内存，零 SQL）=====

    def get_grade(self, grade_id):
        return self.grades.get(grade_id)

    def get_class(self, class_id):
        return self.classes.get(class_id)

    def get_classes_by_grade(self, grade_id):
        return self.classes_by_grade.get(grade_id, [])

    def get_subject(self, subject_id):
        return self.subjects.get(subject_id)

    def get_teacher(self, teacher_id):
        return self.teachers.get(teacher_id)

    def get_current_semester(self):
        return self.current_semester

    def get_student(self, student_id):
        return self.students.get(student_id)

    def get_students_by_class(self, class_id):
        return self.students_by_class.get(class_id, [])

    def get_students_by_grade(self, grade_id):
        return self.students_by_grade.get(grade_id, [])

    def get_all_students_in_school(self):
        return self.students_in_school

    def get_exams_by_grade(self, grade_id):
        return self.exams_by_grade.get(grade_id, [])

    def get_exam(self, exam_id):
        return self.exams.get(exam_id)

    # 成绩缓存：考试级
    def get_scores_for_exam(self, exam_id, session=None):
        if exam_id not in self.scores_cache:
            if session is None:
                return {}
            from src.edu_system.models import Score, Subject

            rows = (
                session.query(Score.student_id, Subject.name, Score.score)
                .join(Subject)
                .filter(Score.exam_id == exam_id)
                .all()
            )
            d = defaultdict(dict)
            for sid, subj, score in rows:
                d[sid][subj] = score
            self.scores_cache[exam_id] = d
        return self.scores_cache[exam_id]

    def invalidate_exam_scores(self, exam_id):
        self.scores_cache.pop(exam_id, None)

    # 内存模式筛选/排序（学生列表用）
    def filter_students(self, grade_id=None, class_id=None, keyword=None, status="在校"):
        """内存筛选，返回 Student 列表"""
        if class_id:
            candidates = self.students_by_class.get(class_id, [])
        elif grade_id:
            candidates = self.students_by_grade.get(grade_id, [])
        else:
            candidates = self.students_in_school

        if keyword:
            kw = keyword.strip()
            candidates = [
                s
                for s in candidates
                if kw in s.name
                or kw in (s.student_code or "")
                or kw in (s.id_card or "")
                or kw in (s.phone or "")
            ]

        if status and status != "全部":
            candidates = [s for s in candidates if s.status == status]

        return candidates


# 全局单例
cache = MemoryCache()


def get_cache() -> MemoryCache:
    return cache
