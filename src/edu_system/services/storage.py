"""
文件存储服务
支持：本地分目录存储、SHA256 去重、访问控制、孤儿文件清理
"""

import hashlib
import mimetypes
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import relationship

# 使用模型层的 Base，确保关系能正确解析
from edu_system.models import Base

# 注意：不在此处 import edu_system.database（models → storage → database → models 循环导入）。
# get_session 在函数内延迟导入。此文件被 models/__init__.py 末尾 import 以注册 StoredFile 表。


@dataclass
class FileInfo:
    """文件信息"""

    id: int
    sha256: str
    original_name: str
    mime_type: str
    size: int
    school_id: int
    semester_id: int
    file_type: str  # photo/excel/word/pdf/admit_card/transcript/archive
    stored_path: str
    uploader_id: int
    created_at: datetime
    access_count: int = 0


class StoredFile(Base):
    """存储文件记录表"""

    __tablename__ = "stored_files"

    id = Column(Integer, primary_key=True)
    sha256 = Column(String(64), nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False, index=True)
    file_type = Column(
        String(50), nullable=False, index=True
    )  # photo/excel/word/pdf/admit_card/transcript/archive
    stored_path = Column(String(500), nullable=False)  # 相对存储路径
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    access_count = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_stored_file_semester_type", "semester_id", "file_type"),
        Index("idx_stored_file_sha256", "sha256"),
    )

    # 使用字符串引用避免循环导入问题
    school = relationship("School", foreign_keys=[school_id])
    semester = relationship("Semester", foreign_keys=[semester_id])
    uploader = relationship("User", foreign_keys=[uploader_id])


class StorageService:
    """文件存储服务"""

    # 文件类型配置
    FILE_TYPES = {
        "photo": {
            "max_size": 10 * 1024 * 1024,
            "allowed_mimes": ["image/jpeg", "image/png", "image/webp"],
        },
        "excel": {
            "max_size": 50 * 1024 * 1024,
            "allowed_mimes": [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
            ],
        },
        "word": {
            "max_size": 50 * 1024 * 1024,
            "allowed_mimes": [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            ],
        },
        "pdf": {"max_size": 100 * 1024 * 1024, "allowed_mimes": ["application/pdf"]},
        "admit_card": {"max_size": 50 * 1024 * 1024, "allowed_mimes": ["application/pdf"]},
        "transcript": {
            "max_size": 50 * 1024 * 1024,
            "allowed_mimes": [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ],
        },
        "archive": {
            "max_size": 500 * 1024 * 1024,
            "allowed_mimes": ["application/zip", "application/x-tar", "application/gzip"],
        },
    }

    def __init__(self, base_path: str = "项目根目录/uploads", verbose=False):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    def log(self, msg):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _get_storage_dir(self, school_id: int, semester_id: int, file_type: str) -> Path:
        """获取存储目录：uploads/{school_id}/{semester_id}/{file_type}/"""
        dir_path = self.base_path / str(school_id) / str(semester_id) / file_type
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def _compute_sha256(self, file_obj: BinaryIO) -> str:
        """计算文件 SHA256"""
        h = hashlib.sha256()
        file_obj.seek(0)
        for chunk in iter(lambda: file_obj.read(8192), b""):
            h.update(chunk)
        file_obj.seek(0)
        return h.hexdigest()

    def _get_mime_type(self, filename: str, file_obj: BinaryIO = None) -> str:
        """获取 MIME 类型"""
        mime, _ = mimetypes.guess_type(filename)
        if mime:
            return mime
        return "application/octet-stream"

    def validate_file(
        self, file_type: str, filename: str, file_obj: BinaryIO, mime_type: str = None
    ) -> tuple[bool, str]:
        """验证文件是否符合类型要求"""
        if file_type not in self.FILE_TYPES:
            return False, f"未知文件类型: {file_type}"

        config = self.FILE_TYPES[file_type]

        # 检查大小
        file_obj.seek(0, 2)  # 移到末尾
        size = file_obj.tell()
        file_obj.seek(0)

        if size > config["max_size"]:
            return (
                False,
                f"文件过大: {size} > {config['max_size']} ({config['max_size'] / 1024 / 1024:.1f}MB)",
            )

        # 检查 MIME
        if mime_type is None:
            mime_type = self._get_mime_type(filename)

        if mime_type not in config["allowed_mimes"]:
            return False, f"不支持的文件格式: {mime_type}，允许: {config['allowed_mimes']}"

        return True, ""

    def save_file(
        self,
        school_id: int,
        semester_id: int,
        file_type: str,
        filename: str,
        file_obj: BinaryIO,
        uploader_id: int = None,
        mime_type: str = None,
    ) -> StoredFile:
        """
        保存文件
        返回 StoredFile 记录（含去重逻辑）
        """
        self.log(f"保存文件: {filename} -> {file_type}")

        # 验证
        if mime_type is None:
            mime_type = self._get_mime_type(filename, file_obj)

        ok, msg = self.validate_file(file_type, filename, file_obj, mime_type)
        if not ok:
            raise ValueError(msg)

        # 计算 SHA256
        sha256 = self._compute_sha256(file_obj)

        # 检查是否已存在（去重）
        from edu_system.database import get_session  # 延迟导入，避免 models↔database 循环

        session = get_session()
        existing = (
            session.query(StoredFile)
            .filter(
                StoredFile.sha256 == sha256,
                StoredFile.school_id == school_id,
                StoredFile.semester_id == semester_id,
            )
            .first()
        )

        if existing:
            self.log(f"文件已存在（去重）: {sha256[:16]}...")
            # 更新访问计数
            existing.access_count += 1
            session.commit()
            return existing

        # 生成存储路径
        storage_dir = self._get_storage_dir(school_id, semester_id, file_type)
        stored_name = f"{sha256[:16]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        stored_path = storage_dir / stored_name

        # 写入文件
        file_obj.seek(0)
        with open(stored_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)

        # 记录元数据
        file_record = StoredFile(
            sha256=sha256,
            original_name=filename,
            mime_type=mime_type,
            size=stored_path.stat().st_size,
            school_id=school_id,
            semester_id=semester_id,
            file_type=file_type,
            stored_path=str(stored_path.relative_to(self.base_path)),
            uploader_id=uploader_id,
        )
        session.add(file_record)
        session.commit()

        self.log(f"文件已保存: {stored_path} ({file_record.size} bytes)")
        return file_record

    def get_file(self, file_id: int) -> StoredFile | None:
        """获取文件记录"""
        from edu_system.database import get_session  # 延迟导入，避免 models↔database 循环

        session = get_session()
        return session.query(StoredFile).get(file_id)

    def get_file_by_sha256(
        self, sha256: str, school_id: int, semester_id: int
    ) -> StoredFile | None:
        """按 SHA256 查找文件"""
        from edu_system.database import get_session  # 延迟导入，避免 models↔database 循环

        session = get_session()
        return (
            session.query(StoredFile)
            .filter(
                StoredFile.sha256 == sha256,
                StoredFile.school_id == school_id,
                StoredFile.semester_id == semester_id,
            )
            .first()
        )

    def read_file(self, file_id: int) -> bytes | None:
        """读取文件内容"""
        file_record = self.get_file(file_id)
        if not file_record:
            return None

        full_path = self.base_path / file_record.stored_path
        if not full_path.exists():
            return None

        with open(full_path, "rb") as f:
            return f.read()

    def delete_file(self, file_id: int, force: bool = False) -> bool:
        """删除文件（软删除：仅删除记录，保留物理文件供去重）"""
        from edu_system.database import get_session  # 延迟导入，避免 models↔database 循环

        session = get_session()
        file_record = session.query(StoredFile).get(file_id)
        if not file_record:
            return False

        # 检查是否有其他记录引用同一 SHA256
        ref_count = (
            session.query(StoredFile).filter(StoredFile.sha256 == file_record.sha256).count()
        )

        if ref_count <= 1 and not force:
            # 最后一个引用，删除物理文件
            full_path = self.base_path / file_record.stored_path
            if full_path.exists():
                full_path.unlink()
                self.log(f"物理文件已删除: {full_path}")

        session.delete(file_record)
        session.commit()
        return True

    def list_files(
        self,
        school_id: int = None,
        semester_id: int = None,
        file_type: str = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """列出文件"""
        from edu_system.database import get_session  # 延迟导入，避免 models↔database 循环

        session = get_session()
        query = session.query(StoredFile)

        if school_id:
            query = query.filter(StoredFile.school_id == school_id)
        if semester_id:
            query = query.filter(StoredFile.semester_id == semester_id)
        if file_type:
            query = query.filter(StoredFile.file_type == file_type)

        total = query.count()
        query = query.order_by(StoredFile.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        files = []
        for f in query.all():
            files.append(
                {
                    "id": f.id,
                    "sha256": f.sha256[:16] + "...",
                    "original_name": f.original_name,
                    "mime_type": f.mime_type,
                    "size": f.size,
                    "size_mb": round(f.size / 1024 / 1024, 2),
                    "school_id": f.school_id,
                    "semester_id": f.semester_id,
                    "file_type": f.file_type,
                    "uploader_id": f.uploader_id,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "access_count": f.access_count,
                }
            )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "files": files,
        }

    def cleanup_orphans(self) -> int:
        """清理孤儿文件（物理文件存在但数据库无记录）"""
        self.log("开始清理孤儿文件...")

        from edu_system.database import get_session  # 延迟导入，避免 models↔database 循环

        session = get_session()
        # 获取所有数据库记录的存储路径
        db_paths = set()
        for f in session.query(StoredFile.stored_path).all():
            db_paths.add(f.stored_path)

        # 扫描物理文件
        orphan_count = 0
        for root, dirs, files in os.walk(self.base_path):
            for fname in files:
                fpath = Path(root) / fname
                rel_path = fpath.relative_to(self.base_path)
                if str(rel_path) not in db_paths:
                    if self.verbose:
                        self.log(f"删除孤儿文件: {rel_path}")
                    fpath.unlink()
                    orphan_count += 1

        # 清理空目录
        for root, dirs, files in os.walk(self.base_path, topdown=False):
            for dname in dirs:
                dpath = Path(root) / dname
                if not any(dpath.iterdir()):
                    dpath.rmdir()

        self.log(f"孤儿文件清理完成: 删除 {orphan_count} 个")
        return orphan_count

    def get_storage_stats(self) -> dict[str, Any]:
        """获取存储统计"""
        from edu_system.database import get_session  # 延迟导入，避免 models↔database 循环

        session = get_session()

        total_files = session.query(StoredFile).count()
        total_size = session.query(func.sum(StoredFile.size)).scalar() or 0

        # 按类型统计
        by_type = {}
        for ftype in self.FILE_TYPES.keys():
            count = session.query(StoredFile).filter(StoredFile.file_type == ftype).count()
            size = (
                session.query(func.sum(StoredFile.size))
                .filter(StoredFile.file_type == ftype)
                .scalar()
                or 0
            )
            by_type[ftype] = {"count": count, "size": size, "size_mb": round(size / 1024 / 1024, 2)}

        # 去重率
        unique_sha = session.query(func.count(func.distinct(StoredFile.sha256))).scalar()
        dedup_rate = (1 - unique_sha / total_files) * 100 if total_files > 0 else 0

        return {
            "total_files": total_files,
            "unique_files": unique_sha,
            "dedup_rate_percent": round(dedup_rate, 2),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_size_gb": round(total_size / 1024 / 1024 / 1024, 3),
            "by_type": by_type,
            "base_path": str(self.base_path),
        }


def get_storage_service(base_path: str = None, verbose=False) -> StorageService:
    """获取存储服务实例"""
    if base_path is None:
        base_path = "项目根目录/uploads"
    return StorageService(base_path, verbose=verbose)
