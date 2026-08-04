"""
成绩统计服务 — SQLAlchemy 1.4 兼容版
"""

from collections import defaultdict
from itertools import groupby

from sqlalchemy.orm import Session

from edu_system.models import Class as ClassModel
from edu_system.models import Exam, Grade, Score, Student, Subject


class ScoreService:
    def __init__(self, session: Session):
        self.session = session

    def convert_scores(
        self,
        exam_id: int,
        full_marks: dict | None = None,
        target_full_mark: float = 100.0,
    ) -> int:
        """把原始分折算为目标满分制折算分（Sprint 3.7.16）

        规则: converted_score = round(score / full_mark * target_full_mark, 1)
        - 原始分满分（full_marks）与折算目标满分（target_full_mark）均可灵活设置
        - 仅折算已录入、未缺考的分数；幂等可重跑
        - full_marks: {subject_id: 原始分满分}；缺省用 Subject.full_mark
        返回: 折算的分数条数
        """
        if full_marks is None:
            full_marks = {
                int(s.id): float(s.full_mark or 100) for s in self.session.query(Subject).all()
            }

        scores = self.session.query(Score).filter(Score.exam_id == exam_id).all()
        count = 0
        for sc in scores:
            if sc.score is None:
                continue  # 缺考不折算
            fm = full_marks.get(int(sc.subject_id), 100.0)
            if not fm:
                continue
            sc.converted_score = round(float(sc.score) / fm * target_full_mark, 1)
            count += 1
        self.session.commit()
        return count

    def get_exam_scores(self, exam_id: int) -> tuple:
        """获取某次考试的成绩矩阵 - 显示该年级所有学生，即使无成绩"""
        exam = self.session.get(Exam, exam_id)
        if not exam or not exam.grade_id:
            return [], [], {}

        # 获取该年级所有在校学生
        students_base = (
            self.session.query(
                Student.id.label("student_id"),
                Student.name,
                Student.student_no,
                ClassModel.name.label("class_name"),
                Grade.name.label("grade_name"),
            )
            .select_from(Student)
            .join(ClassModel)
            .join(Grade)
            .filter(Student.status == "在校", Grade.id == exam.grade_id)
            .order_by(Grade.sort_order, ClassModel.name, Student.student_no)
            .all()
        )

        # 获取考试科目
        subjects = [s.name for s in self.session.query(Subject).order_by(Subject.sort_order).all()]
        subject_configs = {
            s.name: {"full_mark": s.full_mark, "pass_line": s.pass_line}
            for s in self.session.query(Subject).all()
        }

        # 获取已有成绩
        score_rows = (
            self.session.query(Score.student_id, Subject.name.label("subject"), Score.score)
            .join(Subject)
            .filter(Score.exam_id == exam_id)
            .all()
        )

        # 构建成绩字典
        scores_dict = defaultdict(dict)
        for r in score_rows:
            scores_dict[r.student_id][r.subject] = r.score

        students = []
        for stu in students_base:
            students.append(
                {
                    "class_name": stu.class_name,
                    "name": stu.name,
                    "student_no": stu.student_no,
                    "scores": scores_dict.get(stu.student_id, {}),
                    "student_id": stu.student_id,
                }
            )

        subjects = self.session.query(Subject.name).order_by(Subject.sort_order).all()
        subjects = [s[0] for s in subjects]

        return students, subjects, subject_configs

    def calc_class_stats(self, exam_id: int) -> list[dict]:
        students, subjects, configs = self.get_exam_scores(exam_id)
        by_class = defaultdict(list)
        for s in students:
            by_class[s["class_name"]].append(s)
        result = []
        for cls_name in sorted(by_class):
            cls_students = by_class[cls_name]
            cls_stats = {"class_name": cls_name, "count": len(cls_students)}
            for subj in subjects:
                scores = [
                    s["scores"].get(subj) for s in cls_students if s["scores"].get(subj) is not None
                ]
                if not scores:
                    continue
                valid = [x for x in scores if x is not None]
                if valid:
                    cls_stats[f"{subj}_avg"] = round(sum(valid) / len(valid), 2)
                    cfg = configs.get(subj, {"pass_line": 60})
                    cls_stats[f"{subj}_pass"] = round(
                        sum(1 for x in valid if x >= cfg["pass_line"]) / len(valid) * 100, 1
                    )
                else:
                    cls_stats[f"{subj}_avg"] = 0
                    cls_stats[f"{subj}_pass"] = 0
            result.append(cls_stats)
        return result

    def calc_grade_ranks(self, exam_id: int) -> list[dict]:
        students, subjects, _ = self.get_exam_scores(exam_id)
        for s in students:
            valid_scores = [v for v in s["scores"].values() if v is not None]
            s["total"] = round(sum(valid_scores), 1) if valid_scores else None

        ranked = sorted([s for s in students if s["total"] is not None], key=lambda x: -x["total"])
        for i, s in enumerate(ranked):
            s["grade_rank"] = i + 1
            if i > 0 and s["total"] == ranked[i - 1]["total"]:
                s["grade_rank"] = ranked[i - 1]["grade_rank"]

        for cls_name, group in groupby(
            sorted(students, key=lambda x: x["class_name"]),
            key=lambda x: x["class_name"],
        ):
            cls_list = sorted(
                [s for s in group if s["total"] is not None], key=lambda x: -x["total"]
            )
            for i, s in enumerate(cls_list):
                s["class_rank"] = i + 1
                if i > 0 and s["total"] == cls_list[i - 1]["total"]:
                    s["class_rank"] = cls_list[i - 1]["class_rank"]
        return students

    def compare_exams(self, exam_id_1: int, exam_id_2: int) -> list[dict]:
        stu_1 = {s["name"]: s for s in self.calc_grade_ranks(exam_id_1)}
        stu_2 = {s["name"]: s for s in self.calc_grade_ranks(exam_id_2)}
        result = []
        for name, s2 in stu_2.items():
            s1 = stu_1.get(name)
            if not s1:
                continue
            result.append(
                {
                    "name": name,
                    "class_name": s2["class_name"],
                    "total_prev": s1.get("total"),
                    "total_cur": s2.get("total"),
                    "diff": round((s2.get("total") or 0) - (s1.get("total") or 0), 1),
                    "rank_prev": s1.get("grade_rank"),
                    "rank_cur": s2.get("grade_rank"),
                    "rank_change": (s1.get("grade_rank") or 0) - (s2.get("grade_rank") or 0),
                }
            )
        return sorted(result, key=lambda x: -(x["diff"] or 0))
