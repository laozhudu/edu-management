"""
统计预计算服务
核心策略：
1. 预计算落表 SemesterStatsCache，界面查询零实时聚合
2. 事件驱动增量刷新，避免全量重算
3. 版本控制 + HTTP 304，界面秒级响应
"""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from edu_system.database import get_active_semester
from edu_system.models import Class, Exam, Grade, Score, SemesterStatsCache, Student, Teacher

# 核心指标键常量
METRIC_KEYS = {
    # 学生维度
    "student_count": "学生数量",
    "student_male": "男生数",
    "student_female": "女生数",
    "student_boarding": "住校生数",
    "student_day": "走读生数",
    # 班级维度
    "class_count": "班级数量",
    "class_avg_size": "平均班额",
    "class_max_size": "最大班额",
    "class_min_size": "最小班额",
    # 教师维度
    "teacher_count": "教师数量",
    "teacher_title_stats": "职称统计",
    # 学科维度
    "subject_count": "学科数量",
    # 成绩维度
    "score_avg": "平均分",
    "score_pass_rate": "及格率",
    "score_good_rate": "良好率",
    "score_excellent_rate": "优秀率",
    "score_distribution": "分段分布",
    # 考试维度
    "exam_count": "考试场次",
    "exam_participation": "参考率",
    # 排名维度
    "class_rank_avg": "班级平均排名",
    "grade_rank_avg": "年级平均排名",
}


class StatisticsService:
    """统计计算服务：负责全量/增量计算，写入 SemesterStatsCache"""

    def __init__(self, session: Session):
        self.session = session
        self.semester_id = get_active_semester()

    def set_semester(self, semester_id: int):
        self.semester_id = semester_id

    # ===== 核心计算方法 =====

    def compute_student_metrics(self, entity_type: str, entity_id: int) -> dict[str, float]:
        """计算学生相关指标"""
        query = self.session.query(Student).filter(
            Student.semester_id == self.semester_id, Student.status == "在校"
        )

        if entity_type == "class" and entity_id:
            query = query.filter(Student.class_id == entity_id)
        elif entity_type == "grade" and entity_id:
            query = query.join(Class).filter(Class.grade_id == entity_id)
        elif entity_type == "school":
            pass  # 全校

        students = query.all()
        total = len(students)
        if total == 0:
            return {
                k: 0.0
                for k in [
                    "student_count",
                    "student_male",
                    "student_female",
                    "student_boarding",
                    "student_day",
                ]
            }

        male = sum(1 for s in students if s.gender == "男")
        female = total - male
        boarding = sum(1 for s in students if s.boarding == "住校")
        day = total - boarding

        return {
            "student_count": float(total),
            "student_male": float(male),
            "student_female": float(female),
            "student_boarding": float(boarding),
            "student_day": float(day),
        }

    def compute_class_metrics(self, entity_type: str, entity_id: int) -> dict[str, float]:
        """计算班级相关指标"""
        query = self.session.query(Class).filter(Class.semester_id == self.semester_id)

        if entity_type == "class" and entity_id:
            query = query.filter(Class.id == entity_id)
        elif entity_type == "grade" and entity_id:
            query = query.filter(Class.grade_id == entity_id)
        elif entity_type == "school":
            pass

        classes = query.all()
        total = len(classes)
        if total == 0:
            return {
                k: 0.0
                for k in ["class_count", "class_avg_size", "class_max_size", "class_min_size"]
            }

        # 统计每班人数
        class_ids = [c.id for c in classes]
        student_counts = (
            self.session.query(Student.class_id, func.count(Student.id))
            .filter(
                Student.class_id.in_(class_ids),
                Student.semester_id == self.semester_id,
                Student.status == "在校",
            )
            .group_by(Student.class_id)
            .all()
        )

        count_map = {cid: cnt for cid, cnt in student_counts}
        sizes = [count_map.get(c.id, 0) for c in classes]

        return {
            "class_count": float(total),
            "class_avg_size": sum(sizes) / total if total else 0.0,
            "class_max_size": float(max(sizes)) if sizes else 0.0,
            "class_min_size": float(min(sizes)) if sizes else 0.0,
        }

    def compute_teacher_metrics(self, entity_type: str, entity_id: int) -> dict[str, float]:
        """计算教师相关指标"""
        query = self.session.query(Teacher).filter(Teacher.semester_id == self.semester_id)
        # 简化：暂不按 entity 过滤教师
        teachers = query.all()
        total = len(teachers)

        title_stats = defaultdict(int)
        for t in teachers:
            if t.title:
                title_stats[t.title] += 1

        return {
            "teacher_count": float(total),
            "teacher_title_stats": float(len(title_stats)),  # 简化存储
        }

    def compute_score_metrics(
        self, entity_type: str, entity_id: int, exam_id: int | None = None
    ) -> dict[str, float]:
        """计算成绩相关指标"""
        query = self.session.query(Score).join(Exam).filter(Exam.semester_id == self.semester_id)

        if exam_id:
            query = query.filter(Score.exam_id == exam_id)

        if entity_type == "class" and entity_id:
            query = query.join(Student).filter(Student.class_id == entity_id)
        elif entity_type == "grade" and entity_id:
            query = query.join(Student).join(Class).filter(Class.grade_id == entity_id)
        elif entity_type == "subject" and entity_id:
            query = query.filter(Score.subject_id == entity_id)
        elif entity_type == "exam" and exam_id:
            pass  # 已过滤

        scores = query.filter(Score.score.isnot(None)).all()
        if not scores:
            return {
                k: 0.0
                for k in [
                    "score_avg",
                    "score_pass_rate",
                    "score_good_rate",
                    "score_excellent_rate",
                    "score_distribution",
                ]
            }

        values = [s.score for s in scores]
        avg = sum(values) / len(values)

        # 获取及格线等（简化：假设 60/80/90）
        pass_count = sum(1 for v in values if v >= 60)
        good_count = sum(1 for v in values if v >= 80)
        excellent_count = sum(1 for v in values if v >= 90)

        # 分段分布
        dist = defaultdict(int)
        for v in values:
            if v < 60:
                dist["<60"] += 1
            elif v < 70:
                dist["60-69"] += 1
            elif v < 80:
                dist["70-79"] += 1
            elif v < 90:
                dist["80-89"] += 1
            else:
                dist["90+"] += 1

        total = len(values)
        return {
            "score_avg": round(avg, 2),
            "score_pass_rate": round(pass_count / total * 100, 2),
            "score_good_rate": round(good_count / total * 100, 2),
            "score_excellent_rate": round(excellent_count / total * 100, 2),
            "score_distribution": float(len(dist)),  # 简化
        }

    def compute_exam_metrics(self) -> dict[str, float]:
        """计算考试维度指标"""
        exams = self.session.query(Exam).filter(Exam.semester_id == self.semester_id).all()

        total = len(exams)
        if total == 0:
            return {"exam_count": 0.0, "exam_participation": 0.0}

        # 计算平均参考率
        participations = []
        for e in exams:
            scores = self.session.query(Score).filter(Score.exam_id == e.id).all()
            attended = sum(1 for s in scores if s.score is not None)
            total_stu = len(scores)
            if total_stu > 0:
                participations.append(attended / total_stu * 100)

        avg_participation = sum(participations) / len(participations) if participations else 0

        return {
            "exam_count": float(total),
            "exam_participation": round(avg_participation, 2),
        }

    # ===== 统一入口 =====

    def compute_all_metrics(
        self, entity_type: str, entity_id: int, exam_id: int | None = None
    ) -> dict[str, float]:
        """计算实体的所有指标"""
        metrics = {}

        # 根据实体类型计算不同维度指标
        if entity_type in ("student", "class", "grade", "school"):
            metrics.update(self.compute_student_metrics(entity_type, entity_id))

        if entity_type in ("class", "grade", "school"):
            metrics.update(self.compute_class_metrics(entity_type, entity_id))

        if entity_type in ("teacher", "school"):
            metrics.update(self.compute_teacher_metrics(entity_type, entity_id))

        if entity_type in ("score", "class", "grade", "subject", "exam", "school"):
            metrics.update(self.compute_score_metrics(entity_type, entity_id))

        if entity_type in ("exam", "school"):
            metrics.update(self.compute_exam_metrics())

        return metrics

    # ===== 缓存写入 =====

    def save_metrics(
        self, entity_type: str, entity_id: int, metrics: dict[str, float], version: int
    ):
        """批量写入缓存表"""
        now = datetime.now()
        for key, value in metrics.items():
            cache = SemesterStatsCache(
                semester_id=self.semester_id,
                entity_type=entity_type,
                entity_id=entity_id,
                metric_key=key,
                metric_value=value,
                version=version,
                computed_at=now,
            )
            # 使用 merge 实现 upsert
            self.session.merge(cache)
        self.session.commit()

    # ===== 全量/增量计算入口 =====

    def full_recompute(self) -> int:
        """全量重算所有缓存，返回新版本号"""
        # 获取当前最大版本号
        max_version = (
            self.session.query(func.max(SemesterStatsCache.version))
            .filter(SemesterStatsCache.semester_id == self.semester_id)
            .scalar()
            or 0
        )
        new_version = max_version + 1

        # 删除旧版本
        self.session.query(SemesterStatsCache).filter(
            SemesterStatsCache.semester_id == self.semester_id
        ).delete()

        # 1. 学期汇总 (entity_id=0)
        metrics = self.compute_all_metrics("school", 0)
        self.save_metrics("school", 0, metrics, new_version)

        # 2. 各年级
        grades = self.session.query(Grade).all()
        for g in grades:
            metrics = self.compute_all_metrics("grade", g.id)
            self.save_metrics("grade", g.id, metrics, new_version)

        # 3. 各班级
        classes = self.session.query(Class).filter(Class.semester_id == self.semester_id).all()
        for c in classes:
            metrics = self.compute_all_metrics("class", c.id)
            self.save_metrics("class", c.id, metrics, new_version)

        # 4. 各学科（考试级）
        exams = self.session.query(Exam).filter(Exam.semester_id == self.semester_id).all()
        for e in exams:
            metrics = self.compute_all_metrics("exam", e.id, exam_id=e.id)
            self.save_metrics("exam", e.id, metrics, new_version)

        return new_version

    def incremental_recompute(self, dirty_entities: list[dict]) -> int:
        """增量重算：只重算标记脏位的实体"""
        max_version = (
            self.session.query(func.max(SemesterStatsCache.version))
            .filter(SemesterStatsCache.semester_id == self.semester_id)
            .scalar()
            or 0
        )
        new_version = max_version + 1

        for item in dirty_entities:
            entity_type = item["entity_type"]
            entity_id = item["entity_id"]
            exam_id = item.get("exam_id")

            # 删除旧缓存
            self.session.query(SemesterStatsCache).filter(
                SemesterStatsCache.semester_id == self.semester_id,
                SemesterStatsCache.entity_type == entity_type,
                SemesterStatsCache.entity_id == entity_id,
            ).delete()

            # 重新计算并保存
            metrics = self.compute_all_metrics(entity_type, entity_id, exam_id)
            self.save_metrics(entity_type, entity_id, metrics, new_version)

        return new_version

    def calculate_rank(self, exam_id: int, scope: str = "class") -> dict:
        """排名计算（简化实现：返回计算结果统计）"""
        from edu_system.models import Class, Score, Student

        # 获取考试的所有成绩
        scores = (
            self.session.query(Score)
            .filter(Score.exam_id == exam_id, Score.score.isnot(None))
            .all()
        )

        if not scores:
            return {"message": "无成绩数据", "ranked": 0}

        # 按 scope 分组计算排名
        if scope == "class":
            # 班级内排名
            ranked = 0
            class_scores = defaultdict(list)
            for s in scores:
                student = self.session.query(Student).filter(Student.id == s.student_id).first()
                if student and student.class_id:
                    class_scores[student.class_id].append((s.student_id, s.score))

            for class_id, stu_scores in class_scores.items():
                stu_scores.sort(key=lambda x: x[1], reverse=True)
                for rank, (stu_id, score) in enumerate(stu_scores, 1):
                    # 这里可以更新 Score.rank 字段（如果存在）
                    ranked += 1

            return {"message": "班级排名计算完成", "ranked": ranked}

        elif scope == "grade":
            # 年级内排名
            ranked = 0
            grade_scores = defaultdict(list)
            for s in scores:
                student = self.session.query(Student).filter(Student.id == s.student_id).first()
                if student and student.class_id:
                    cls = self.session.query(Class).filter(Class.id == student.class_id).first()
                    if cls and cls.grade_id:
                        grade_scores[cls.grade_id].append((s.student_id, s.score))

            for grade_id, stu_scores in grade_scores.items():
                stu_scores.sort(key=lambda x: x[1], reverse=True)
                for rank, (stu_id, score) in enumerate(stu_scores, 1):
                    ranked += 1

            return {"message": "年级排名计算完成", "ranked": ranked}

        else:  # school
            # 全校排名
            stu_scores = [(s.student_id, s.score) for s in scores]
            stu_scores.sort(key=lambda x: x[1], reverse=True)
            for rank, (stu_id, score) in enumerate(stu_scores, 1):
                pass  # 可以存储排名

            return {"message": "全校排名计算完成", "ranked": len(stu_scores)}


class StatisticsWorker:
    """后台统计计算 Worker：QThread + 进度条 + 可取消"""

    def __init__(self):
        self._thread = None
        self._cancelled = False
        self._progress_callback = None
        self._finished_callback = None
        self._error_callback = None
        self._mode = "full"  # 'full' 或 'incremental'
        self._dirty_entities = []

    def start_full(self, progress_cb, finished_cb, error_cb):
        """启动全量重算"""
        self._mode = "full"
        self._progress_callback = progress_cb
        self._finished_callback = finished_cb
        self._error_callback = error_cb
        self._cancelled = False
        self._run_in_thread(self._run_full)

    def start_incremental(self, dirty_entities: list[dict], progress_cb, finished_cb, error_cb):
        """启动增量重算"""
        self._mode = "incremental"
        self._dirty_entities = dirty_entities
        self._progress_callback = progress_cb
        self._finished_callback = finished_cb
        self._error_callback = error_cb
        self._cancelled = False
        self._run_in_thread(self._run_incremental)

    def cancel(self):
        self._cancelled = True

    def _run_in_thread(self, target):
        from PyQt5.QtCore import QThread

        self._thread = QThread()
        worker = _StatisticsWorkerRunnable(target, self)
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.finished.connect(self._thread.quit)
        worker.finished.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _run_full(self):
        from edu_system.database import get_session

        session = get_session()
        try:
            run_full_recompute(
                session,
                progress_cb=self._progress_callback,
                finished_cb=self._finished_callback,
                error_cb=self._error_callback,
                cancel_check=lambda: self._cancelled,
            )
        finally:
            session.close()

    def _run_incremental(self):
        from edu_system.database import get_session

        session = get_session()
        try:
            run_incremental_recompute(
                session,
                self._dirty_entities,
                progress_cb=self._progress_callback,
                finished_cb=self._finished_callback,
                error_cb=self._error_callback,
                cancel_check=lambda: self._cancelled,
            )
        finally:
            session.close()


# ============================================================
# M5-B3 后台 Worker 可测试核心（纯函数，不依赖 QThread/全局会话）
# StatisticsWorker 通过 QThread 调用；单测直接调用同步函数
# ============================================================


def run_full_recompute(
    session: Session,
    progress_cb=None,
    finished_cb=None,
    error_cb=None,
    cancel_check=None,
) -> bool:
    """全量重算（同步，可取消）

    返回是否完成（False = 中途取消或异常）。
    cancel_check: 无参可调用，返回 True 时提前终止。
    """
    try:
        service = StatisticsService(session)
        if progress_cb:
            progress_cb(0, "开始全量重算...")

        # 进度固定 5 步：学期汇总/年级/班级/考试/完成
        # （update_progress 调用次数与 total_steps 必须一致，避免百分比溢出）
        total_steps = 5
        current = 0

        def update_progress(step_name: str):
            nonlocal current
            current += 1
            if progress_cb and not (cancel_check and cancel_check()):
                progress_cb(int(current / total_steps * 100), step_name)

        if cancel_check and cancel_check():
            return False

        update_progress("学期汇总")
        service = StatisticsService(session)
        service.full_recompute()

        if cancel_check and cancel_check():
            return False

        update_progress("年级统计")
        update_progress("班级统计")
        update_progress("考试统计")

        if not (cancel_check and cancel_check()):
            update_progress("完成")
            if finished_cb:
                finished_cb("全量重算完成")
        return True
    except Exception as e:
        if error_cb:
            error_cb(str(e))
        return False


def run_incremental_recompute(
    session: Session,
    dirty_entities: list[dict],
    progress_cb=None,
    finished_cb=None,
    error_cb=None,
    cancel_check=None,
) -> bool:
    """增量重算（同步，可取消）

    返回是否完成（False = 中途取消或异常）。
    """
    try:
        service = StatisticsService(session)
        total = len(dirty_entities)

        for i, item in enumerate(dirty_entities):
            if cancel_check and cancel_check():
                return False
            if progress_cb:
                progress_cb(
                    int((i + 1) / total * 100) if total else 100,
                    f"增量重算: {item['entity_type']}-{item['entity_id']}",
                )

            service.incremental_recompute([item])

        if not (cancel_check and cancel_check()) and finished_cb:
            finished_cb(f"增量重算完成: {total} 项")
        return True
    except Exception as e:
        if error_cb:
            error_cb(str(e))
        return False


class _StatisticsWorkerRunnable:
    """QThread 运行包装"""

    def __init__(self, target, worker):
        self.target = target
        self.worker = worker
        from PyQt5.QtCore import pyqtSignal

        self.finished = pyqtSignal()

    def run(self):
        try:
            self.target()
        finally:
            self.finished.emit()


# ============================================================
# M5-B2 事件驱动增量刷新
# 业务层数据变更 → mark_stats_dirty() 发布 stats.dirty 事件
# → outbox 轮询触发 handler → 增量重算脏实体 + 失效查询缓存
# ============================================================

# 支持标记脏的实体类型（与 SemesterStatsCache.entity_type 一致）
_DIRTY_ENTITY_TYPES = {"student", "class", "grade", "teacher", "subject", "exam", "school"}


def mark_stats_dirty(
    session: Session,
    entity_type: str,
    entity_id: int,
    semester_id: int | None = None,
    exam_id: int | None = None,
) -> bool:
    """数据变更后标记统计缓存脏（发布 stats.dirty 事件）

    业务层在 student/score/exam 等变更事务内调用：
        mark_stats_dirty(session, "student", stu.id)
        mark_stats_dirty(session, "exam", exam.id, exam_id=exam.id)
    返回是否成功入队（非法实体类型返回 False）。
    """
    if entity_type not in _DIRTY_ENTITY_TYPES:
        return False

    from edu_system.core.event_bus import DomainEvent, EventTypes, event_bus

    payload = {"entity_type": entity_type, "entity_id": entity_id, "exam_id": exam_id}
    if semester_id is not None:
        payload["semester_id"] = semester_id

    event_bus.publish(
        DomainEvent(
            event_type=EventTypes.STATS_DIRTY,
            aggregate_id=f"{entity_type}:{entity_id}",
            payload=payload,
        ),
        session=session,
    )
    return True


def handle_stats_dirty(payload: dict, session: Session | None = None) -> None:
    """stats.dirty 事件处理器：增量重算脏实体并失效查询缓存

    由 outbox 轮询（APScheduler 10s）在事件发布方事务提交后调用。
    session 参数供测试注入；生产环境留空使用全局会话。
    """
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    if entity_type not in _DIRTY_ENTITY_TYPES or not entity_id:
        return

    from edu_system.database import get_active_semester, get_session
    from edu_system.services.cache import invalidate_stats_cache

    semester_id = payload.get("semester_id") or get_active_semester()
    if not semester_id:
        return

    close_session = session is None
    if session is None:
        session = get_session()
    try:
        service = StatisticsService(session)
        service.set_semester(int(semester_id))
        service.incremental_recompute(
            [
                {
                    "entity_type": entity_type,
                    "entity_id": int(entity_id),
                    "exam_id": payload.get("exam_id"),
                }
            ]
        )
        session.commit()
        invalidate_stats_cache(semester_id=int(semester_id))
    finally:
        if close_session:
            session.close()


def register_stats_dirty_handler() -> None:
    """注册 stats.dirty 处理器到全局事件总线（应用启动时调用一次）"""
    from edu_system.core.event_bus import EventTypes, event_bus

    event_bus.register(EventTypes.STATS_DIRTY, handle_stats_dirty)
