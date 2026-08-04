#!/usr/bin/env python3
"""
学期归档脚本
将指定学期归档为只读副本 + 校验和 + 元数据 JSON
归档后原库该学期 status=archived
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from edu_system.database import get_session, init_db_with_defaults
from edu_system.models import Semester, SemesterStatus


class SemesterArchiver:
    def __init__(self, db_path: Path, archive_root: Path, verbose=False):
        self.db_path = db_path
        self.archive_root = archive_root
        self.verbose = verbose
        self.archive_root.mkdir(parents=True, exist_ok=True)

    def log(self, msg):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def sha256_file(self, filepath: Path) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def archive_semester(self, semester_id: int, force=False):
        """归档指定学期"""
        self.log(f"开始归档学期 {semester_id}...")

        session = get_session()
        sem = session.query(Semester).get(semester_id)
        if not sem:
            raise ValueError(f"学期不存在: {semester_id}")

        if sem.status == SemesterStatus.archived and not force:
            self.log(f"学期 {semester_id} 已归档，跳过")
            return False

        # 1. 创建归档目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"school_data_{sem.year_start}_{sem.semester}_{timestamp}"
        archive_dir = self.archive_root / archive_name
        archive_dir.mkdir(parents=True, exist_ok=True)

        # 2. 复制数据库文件
        db_backup = archive_dir / "school_data.db"
        shutil.copy2(self.db_path, db_backup)
        self.log(f"数据库已复制: {db_backup}")

        # 3. 计算校验和
        sha256 = self.sha256_file(db_backup)
        self.log(f"SHA256: {sha256}")

        # 4. 创建元数据
        metadata = {
            "semester_id": sem.id,
            "semester_label": sem.label,
            "year_start": sem.year_start,
            "semester": sem.semester,
            "academic_year_id": sem.academic_year_id,
            "academic_year_name": sem.academic_year.name if sem.academic_year else None,
            "status_before_archive": (
                sem.status.value if hasattr(sem.status, "value") else str(sem.status)
            ),
            "archived_at": datetime.now().isoformat(),
            "archive_name": archive_name,
            "db_sha256": sha256,
            "db_size": db_backup.stat().st_size,
        }
        meta_path = archive_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        self.log(f"元数据已写入: {meta_path}")

        # 5. 更新原库：将学期状态设为 archived
        sem.status = SemesterStatus.archived
        sem.is_active = False
        session.commit()
        self.log("原库学期状态已更新为 archived")

        # 6. 验证归档
        if self.verify_archive(archive_dir):
            self.log(f"✅ 学期 {semester_id} 归档成功: {archive_dir}")
            return True
        else:
            self.log("❌ 归档验证失败")
            return False

    def verify_archive(self, archive_dir: Path) -> bool:
        """验证归档完整性"""
        db_backup = archive_dir / "school_data.db"
        meta_path = archive_dir / "metadata.json"

        if not db_backup.exists() or not meta_path.exists():
            self.log("错误: 归档文件缺失")
            return False

        with open(meta_path) as f:
            metadata = json.load(f)

        # 校验 SHA256
        actual_sha = self.sha256_file(db_backup)
        if actual_sha != metadata["db_sha256"]:
            self.log(f"SHA256 不匹配: 期望={metadata['db_sha256']} 实际={actual_sha}")
            return False

        # 校验文件大小
        if db_backup.stat().st_size != metadata["db_size"]:
            self.log("文件大小不匹配")
            return False

        self.log("归档验证通过")
        return True

    def list_archives(self):
        """列出所有归档"""
        archives = []
        for item in sorted(self.archive_root.iterdir()):
            if item.is_dir():
                meta_path = item / "metadata.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        metadata = json.load(f)
                    archives.append(
                        {
                            "archive_dir": item.name,
                            "semester_label": metadata.get("semester_label"),
                            "archived_at": metadata.get("archived_at"),
                            "db_size_mb": round(metadata.get("db_size", 0) / 1024 / 1024, 2),
                        }
                    )
        return archives


def main():
    parser = argparse.ArgumentParser(description="学期归档工具")
    parser.add_argument("action", choices=["archive", "list", "verify"], help="操作类型")
    parser.add_argument("--semester-id", type=int, help="学期ID（archive 必需）")
    parser.add_argument("--force", action="store_true", help="强制重新归档")
    parser.add_argument("--archive-name", help="验证指定归档目录")
    parser.add_argument(
        "--db-path", default="项目根目录/data/school_data.db", help="数据库路径"
    )
    parser.add_argument(
        "--archive-root", default="项目根目录/archives", help="归档根目录"
    )
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    archive_root = Path(args.archive_root)

    if not db_path.exists():
        print(f"错误: 数据库不存在: {db_path}")
        return 1

    init_db_with_defaults()

    archiver = SemesterArchiver(db_path, archive_root, verbose=args.verbose)

    if args.action == "archive":
        if not args.semester_id:
            print("错误: archive 操作需要 --semester-id")
            return 1
        success = archiver.archive_semester(args.semester_id, force=args.force)
        return 0 if success else 1
    elif args.action == "list":
        archives = archiver.list_archives()
        for a in archives:
            print(
                f"{a['archive_dir']}: {a['semester_label']} @ {a['archived_at']} ({a['db_size_mb']} MB)"
            )
    elif args.action == "verify":
        if not args.archive_name:
            print("错误: verify 操作需要 --archive-name")
            return 1
        archive_dir = archive_root / args.archive_name
        if archiver.verify_archive(archive_dir):
            print(f"✅ 归档验证通过: {archive_dir}")
        else:
            print(f"❌ 归档验证失败: {archive_dir}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
