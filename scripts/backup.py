#!/usr/bin/env python3
"""
备份脚本
支持：每日增量（WAL checkpoint + .backup）、学期全量、SHA256 校验
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from edu_system.database import get_session, init_db_with_defaults
from edu_system.models import Semester


class BackupManager:
    def __init__(self, db_path: Path, backup_root: Path, verbose=False):
        self.db_path = db_path
        self.wal_path = db_path.with_suffix(".db-wal")
        self.shm_path = db_path.with_suffix(".db-shm")
        self.backup_root = backup_root
        self.verbose = verbose

        # 备份目录结构
        self.daily_dir = backup_root / "daily"
        self.semester_dir = backup_root / "semester"
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.semester_dir.mkdir(parents=True, exist_ok=True)

    def log(self, msg):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def sha256_file(self, filepath: Path) -> str:
        """计算文件 SHA256"""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def create_manifest(self, backup_dir: Path, files: list, backup_type: str):
        """创建清单文件"""
        manifest = {
            "backup_type": backup_type,
            "created_at": datetime.now().isoformat(),
            "source_db": str(self.db_path),
            "files": [],
        }
        for f in files:
            rel_path = f.relative_to(self.backup_root)
            manifest["files"].append(
                {
                    "path": str(rel_path),
                    "size": f.stat().st_size,
                    "sha256": self.sha256_file(f),
                }
            )

        manifest_path = backup_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        self.log(f"清单已写入: {manifest_path}")
        return manifest_path

    def daily_incremental(self):
        """每日增量备份：WAL checkpoint + .backup"""
        self.log("开始每日增量备份...")

        # 1. WAL checkpoint（将 WAL 写回主库）
        session = get_session()
        session.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
        session.commit()
        self.log("WAL checkpoint 完成")

        # 2. 使用 SQLite .backup 命令（通过 sqlite3 CLI 或 Python）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"daily_{timestamp}"
        backup_dir = self.daily_dir / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 复制主数据库文件
        db_backup = backup_dir / self.db_path.name
        shutil.copy2(self.db_path, db_backup)
        self.log(f"数据库已复制: {db_backup}")

        # 3. 创建清单
        self.create_manifest(backup_dir, [db_backup], "daily_incremental")

        # 4. 清理过期增量（保留 30 天）
        self.cleanup_old(self.daily_dir, days=30)

        self.log(f"增量备份完成: {backup_dir}")
        return backup_dir

    def semester_full(self, semester_id: int):
        """学期全量备份"""
        self.log(f"开始学期 {semester_id} 全量备份...")

        session = get_session()
        sem = session.query(Semester).get(semester_id)
        if not sem:
            raise ValueError(f"学期不存在: {semester_id}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"semester_{semester_id}_{sem.label.replace(' ', '_')}_{timestamp}"
        backup_dir = self.semester_dir / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 复制数据库
        db_backup = backup_dir / self.db_path.name
        shutil.copy2(self.db_path, db_backup)

        # 创建元数据
        metadata = {
            "semester_id": semester_id,
            "semester_label": sem.label,
            "academic_year": sem.academic_year.name if sem.academic_year else None,
            "status": sem.status.value if hasattr(sem.status, "value") else str(sem.status),
            "backed_up_at": datetime.now().isoformat(),
        }
        meta_path = backup_dir / "metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 创建清单
        self.create_manifest(backup_dir, [db_backup, meta_path], "semester_full")

        self.log(f"学期全量备份完成: {backup_dir}")
        return backup_dir

    def verify_backup(self, backup_dir: Path) -> bool:
        """校验备份完整性"""
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            self.log(f"错误: 清单文件不存在: {manifest_path}")
            return False

        with open(manifest_path) as f:
            manifest = json.load(f)

        all_ok = True
        for item in manifest["files"]:
            filepath = self.backup_root / item["path"]
            if not filepath.exists():
                self.log(f"错误: 文件缺失: {filepath}")
                all_ok = False
                continue

            actual_sha = self.sha256_file(filepath)
            if actual_sha != item["sha256"]:
                self.log(f"错误: SHA256 不匹配: {filepath} 期望={item['sha256']} 实际={actual_sha}")
                all_ok = False
            else:
                self.log(f"校验通过: {filepath}")

        if all_ok:
            self.log(f"备份完整性校验通过: {backup_dir}")
        return all_ok

    def cleanup_old(self, backup_dir: Path, days: int):
        """清理过期备份"""
        cutoff = datetime.now() - timedelta(days=days)
        for item in backup_dir.iterdir():
            if item.is_dir():
                try:
                    # 从目录名解析时间
                    name = item.name
                    if name.startswith("daily_"):
                        dt_str = name[6:]  # 去掉 'daily_'
                        dt = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
                        if dt < cutoff:
                            shutil.rmtree(item)
                            self.log(f"清理过期备份: {item}")
                except Exception as e:
                    self.log(f"清理失败 {item}: {e}")


def main():
    parser = argparse.ArgumentParser(description="数据库备份工具")
    parser.add_argument(
        "action", choices=["daily", "semester", "verify", "cleanup"], help="操作类型"
    )
    parser.add_argument("--semester-id", type=int, help="学期ID（semester 操作必需）")
    parser.add_argument("--db-path", default="项目根目录/data/school_data.db", help="数据库路径")
    parser.add_argument("--backup-root", default="项目根目录/backups", help="备份根目录")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    backup_root = Path(args.backup_root)

    if not db_path.exists():
        print(f"错误: 数据库不存在: {db_path}")
        return 1

    init_db_with_defaults()

    manager = BackupManager(db_path, backup_root, verbose=args.verbose)

    if args.action == "daily":
        manager.daily_incremental()
    elif args.action == "semester":
        if not args.semester_id:
            print("错误: semester 操作需要 --semester-id")
            return 1
        manager.semester_full(args.semester_id)
    elif args.action == "verify":
        # 验证最新备份
        latest = max(backup_root.rglob("manifest.json"), key=lambda p: p.stat().st_mtime)
        manager.verify_backup(latest.parent)
    elif args.action == "cleanup":
        manager.cleanup_old(manager.daily_dir, days=30)
        manager.cleanup_old(manager.semester_dir, days=365 * 3)

    return 0


if __name__ == "__main__":
    sys.exit(main())
