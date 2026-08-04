"""
服务工厂 — 统一获取服务实例
"""

from sqlalchemy.orm import Session


def get_student_service(session: Session):
    from edu_system.services.student import StudentRepository

    return StudentRepository(session)


def get_score_service(session: Session):
    from edu_system.services.score import ScoreService

    return ScoreService(session)


def get_semester_service(session: Session):
    from edu_system.services.semester import SemesterService

    return SemesterService(session)


def get_import_service(session: Session):
    from edu_system.services.importer import ImportService

    return ImportService(session)


def get_report_service(session: Session):
    from edu_system.services.report import ReportService

    return ReportService(session)


def get_enrollment_service(session: Session):
    from edu_system.services.enrollment import EnrollmentService

    return EnrollmentService(session)
