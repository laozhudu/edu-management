"""
导入导出 API 路由（M5-E7）

- GET  /import/template: 模板下载（entity=student/score，CSV）
- POST /import/preview: 上传 + 字段映射 → 预览（质量报告，不落库）
- POST /import/execute: 执行导入（学生入库）
- GET  /export/students: 学生数据导出（CSV）

复用 ImportExportService（parse/apply_mapping/preview/import_rows）。
"""

from __future__ import annotations

import io
import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db, require_permission
from edu_system.core.permissions import Permission
from edu_system.models import Student, User
from edu_system.services.import_export import (
    ImportOptions,
    ImportExportService,
    ImportFormatError,
)

router = APIRouter(prefix="", tags=["导入导出"])

# 标准字段模板（学生导入表头）
STUDENT_TEMPLATE_COLUMNS = [
    "姓名",
    "性别",
    "座号",
    "全国学籍号",
    "身份证号",
    "出生日期",
    "民族",
    "籍贯",
    "政治面貌",
    "联系电话",
    "居住地址",
    "户籍地址",
    "入学年份",
    "是否住宿",
    "班级",
]

# 模板列 → 模型字段映射
STUDENT_FIELD_MAP = {
    "姓名": "name",
    "性别": "gender",
    "座号": "student_no",
    "全国学籍号": "student_code",
    "身份证号": "id_card",
    "出生日期": "birth_date",
    "民族": "ethnicity",
    "籍贯": "native_place",
    "政治面貌": "political_status",
    "联系电话": "phone",
    "居住地址": "address",
    "户籍地址": "hukou_addr",
    "入学年份": "enroll_year",
    "是否住宿": "boarding",
    "班级": "_class_name",
}


class FieldMappingRequest(BaseModel):
    mapping: dict[str, str]  # {标准列名: 源文件列名}


class ImportPreviewResponse(BaseModel):
    entity: str
    total_rows: int
    valid_rows: int
    error_count: int
    quality_report: dict[str, Any]
    sample: list[dict[str, Any]]


@router.get("/import/template")
def download_template(
    entity: str = "student",
    current_user: User = Depends(get_current_user),
):
    """导入模板下载（CSV，UTF-8 BOM 供 Excel 直接打开）"""
    if entity == "student":
        headers = STUDENT_TEMPLATE_COLUMNS
    else:
        raise HTTPException(status_code=400, detail=f"暂不支持实体类型: {entity}")

    buf = io.StringIO()
    buf.write(",".join(headers) + "\n")
    csv_data = "\ufeff" + buf.getvalue()

    return Response(
        content=csv_data.encode(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{entity}_template.csv"'},
    )


@router.post("/import/preview", response_model=ImportPreviewResponse)
def import_preview(
    file: UploadFile = File(...),
    entity: str = Form("student"),
    mapping_json: str = Form("{}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.STUDENT_IMPORT)),
):
    """上传 + 字段映射 → 预览（质量报告，不落库）"""
    mapping = json.loads(mapping_json) if mapping_json else {}
    data = file.file.read()

    svc = ImportExportService(db)
    try:
        df = svc.parse_bytes(data, file.filename.split(".")[-1].lower())
    except ImportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 应用字段映射（源列 → 标准字段）
    if mapping:
        df = svc.apply_mapping(df, mapping)

    options = ImportOptions(entity=entity, format="csv")
    stage = svc.preview(options, df)

    report = stage.quality_report
    sample = stage.cleaned_df.head(5).to_dict("records") if not stage.cleaned_df.empty else []
    return ImportPreviewResponse(
        entity=entity,
        total_rows=len(df),
        valid_rows=len(stage.rows_to_insert),
        error_count=report.get("error_count", 0),
        quality_report=report,
        sample=sample,
    )


@router.post("/import/execute")
def import_execute(
    file: UploadFile = File(...),
    entity: str = Form("student"),
    mapping_json: str = Form("{}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.STUDENT_IMPORT)),
):
    """执行导入（学生入库）"""
    mapping = json.loads(mapping_json) if mapping_json else {}
    data = file.file.read()

    svc = ImportExportService(db)
    try:
        df = svc.parse_bytes(data, file.filename.split(".")[-1].lower())
    except ImportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if mapping:
        df = svc.apply_mapping(df, mapping)

    options = ImportOptions(entity=entity, format="csv")
    stage = svc.preview(options, df)
    if stage.quality_report.get("error_count", 0) > 0:
        return {
            "success": False,
            "inserted": 0,
            "error": "存在错误行，未入库",
            "error_count": stage.quality_report["error_count"],
        }

    def _insert(rows: list[dict[str, Any]]) -> int:
        count = 0
        for row in rows:
            try:
                student = Student(
                    name=row.get("name", ""),
                    gender=row.get("gender", ""),
                    student_no=row.get("student_no", ""),
                    phone=row.get("phone", ""),
                    enroll_year=row.get("enroll_year") or 0,
                )
                db.add(student)
                count += 1
            except Exception:
                continue
        db.commit()
        return count

    result = svc.import_rows(options, stage, _insert)
    return {
        "success": result.success,
        "inserted": result.inserted,
        "errors": result.error_messages,
    }


@router.get("/export/students")
def export_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.STUDENT_EXPORT)),
):
    """学生数据导出（CSV）"""
    students = db.query(Student).order_by(Student.student_no).all()
    buf = io.StringIO()
    buf.write("\ufeff姓名,性别,座号,入学年份,联系电话\n")
    for s in students:
        buf.write(
            f"{s.name},{s.gender},{s.student_no or ''},{s.enroll_year or ''},{s.phone or ''}\n"
        )
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="students.csv"'},
    )
