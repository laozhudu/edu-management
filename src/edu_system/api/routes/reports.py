"""
报表 API 路由（M6 Sprint 6：报表引擎全集成）

- GET  /api/reports/types         支持的报表类型列表
- POST /api/reports/generate      生成报表（body: type/format/exam_id/output 参数）
- GET  /api/reports/printers      打印机列表
- POST /api/reports/print         打印文件（body: file_paths/copies）

前端可下载生成的报表文件（StreamingResponse）。
"""

import io
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from edu_system.api.deps import get_current_user, get_db
from edu_system.models import User

router = APIRouter(prefix="/reports", tags=["报表"])


class GenerateRequest(BaseModel):
    report_type: str  # exam / change / report_card / certificate
    format: str = "excel"  # excel / word
    exam_id: int | None = None
    semester_id: int | None = None
    certificate_type: str = "award"  # award / certificate
    single_file: bool = True


class PrintRequest(BaseModel):
    file_paths: list[str]
    copies: int = 1


@router.get("/types")
def report_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """支持的报表类型列表（报表工厂注册表）"""
    from edu_system.services.report_factory import ReportFactory

    factory = ReportFactory(db)
    # 复用 ReportFactory.REPORT_TYPES 若存在，否则返回内置清单
    types = getattr(factory, "REPORT_TYPES", None)
    if types:
        return [
            {
                "type": key,
                "name": info.get("name", key),
                "description": info.get("description", ""),
                "formats": info.get("formats", ["excel"]),
            }
            for key, info in types.items()
        ]
    return {
        "report_types": [
            {"type": "exam", "name": "考试标准报表", "formats": ["excel"]},
            {"type": "change", "name": "学籍变动情况表", "formats": ["excel"]},
            {"type": "report_card", "name": "成绩单", "formats": ["word", "excel"]},
            {"type": "certificate", "name": "证书/奖状", "formats": ["word"]},
        ]
    }


@router.post("/generate")
def generate_report(
    request: GenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成报表并返回文件（Excel/Word 下载）"""
    from edu_system.services.report_factory import ReportFactory

    factory = ReportFactory(db)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        try:
            if request.report_type == "exam":
                if not request.exam_id:
                    raise HTTPException(400, "exam 报表需要 exam_id")
                output = tmp_dir / "exam_report.xlsx"
                factory.gen_score_report(request.exam_id, str(output), session=db)
                data = output.read_bytes()
                return StreamingResponse(
                    io.BytesIO(data),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="考试标准报表.xlsx"'},
                )

            elif request.report_type == "change":
                if not request.semester_id:
                    raise HTTPException(400, "change 报表需要 semester_id")
                from edu_system.services.report import ReportService

                svc = ReportService(db)
                output = tmp_dir / "change_report.xlsx"
                svc.generate_change_report(request.semester_id, str(output))
                data = output.read_bytes()
                return StreamingResponse(
                    io.BytesIO(data),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="学籍变动情况表.xlsx"'},
                )

            elif request.report_type == "report_card":
                if not request.exam_id:
                    raise HTTPException(400, "report_card 需要 exam_id")
                from edu_system.services.report import ReportService

                svc = ReportService(db)
                if request.format == "excel":
                    files = svc.generate_report_cards_excel(
                        request.exam_id, str(tmp_dir), single_file=request.single_file
                    )
                else:
                    files = svc.generate_report_cards_word(
                        request.exam_id, str(tmp_dir), single_file=request.single_file
                    )
                if not files:
                    raise HTTPException(404, "无成绩数据可生成")
                data = Path(files[0]).read_bytes()
                media = (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    if request.format != "excel"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                return StreamingResponse(
                    io.BytesIO(data),
                    media_type=media,
                    headers={
                        "Content-Disposition": f'attachment; filename="{Path(files[0]).name}"'
                    },
                )

            elif request.report_type == "certificate":
                if not request.exam_id:
                    raise HTTPException(400, "certificate 需要 exam_id")
                from edu_system.services.report import ReportService

                svc = ReportService(db)
                files = svc.generate_certificate(
                    request.exam_id,
                    str(tmp_dir),
                    certificate_type=request.certificate_type,
                    single_file=request.single_file,
                )
                if not files:
                    raise HTTPException(404, "无获奖学生可生成")
                data = Path(files[0]).read_bytes()
                return StreamingResponse(
                    io.BytesIO(data),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={
                        "Content-Disposition": f'attachment; filename="{Path(files[0]).name}"'
                    },
                )

            else:
                raise HTTPException(400, f"不支持的报表类型: {request.report_type}")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"报表生成失败: {e}")


@router.get("/printers")
def list_printers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """可用打印机列表"""
    from edu_system.services.print_service import PrintService

    svc = PrintService()
    return {"printers": svc.list_printers()}


@router.post("/print")
def print_files(
    request: PrintRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量打印文件"""
    from edu_system.services.print_service import PrintService

    svc = PrintService()
    results = svc.print_files(request.file_paths, copies=request.copies)
    ok = sum(1 for v in results.values() if v)
    return {"success": ok, "total": len(request.file_paths), "results": results}
