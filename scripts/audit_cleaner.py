#!/usr/bin/env python3
"""
审计日志清理服务
支持：月度分表归档、过期分表删除、压缩存储
"""

import argparse
import gzip
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import inspect, text

from edu_system.database import get_session, init_db_with_defaults


class AuditCleaner:
    def __init__(self, db_path: Path, archive_root: Path, verbose=False):
        self.db_path = db_path
        self.archive_root = archive_root
        self.verbose = verbose
        self.archive_root.mkdir(parents=True, exist_ok=True)

    def log(self, msg):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def get_partition_name(self, year: int, month: int) -> str:
        """获取分表名"""
        return f"audit_logs_{year}{month:02d}"

    def get_partition_table(self, year: int, month: int):
        """获取分表对象（动态创建）"""
        table_name = self.get_partition_name(year, month)

        # 检查表是否存在
        session = get_session()
        inspector = inspect(session.bind)
        if table_name not in inspector.get_table_names():
            # 创建分表
            self.create_partition_table(table_name, session)

        # 返回表对象
        from sqlalchemy import MetaData, Table

        metadata = MetaData()
        return Table(table_name, metadata, autoload_with=session.bind)

    def create_partition_table(self, table_name: str, session):
        """创建分表（结构同 audit_logs）"""
        sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name VARCHAR(50) NOT NULL,
            record_id INTEGER NOT NULL,
            action VARCHAR(10) NOT NULL,
            old_values TEXT,
            new_values TEXT,
            operator VARCHAR(20),
            ip VARCHAR(45),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_{table_name}_table ON {table_name}(table_name);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_created ON {table_name}(created_at);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_operator ON {table_name}(operator);
        """
        session.execute(text(sql))
        session.commit()
        self.log(f"分表已创建: {table_name}")

    def create_union_view(self):
        """创建合并视图 audit_logs_all"""
        session = get_session()

        # 获取所有分表
        inspector = inspect(session.bind)
        partitions = [t for t in inspector.get_table_names() if t.startswith("audit_logs_")]

        if not partitions:
            self.log("无分表，跳过视图创建")
            return

        union_parts = []
        for p in sorted(partitions):
            union_parts.append(f"SELECT * FROM {p}")

        view_sql = f"""
        DROP VIEW IF EXISTS audit_logs_all;
        CREATE VIEW audit_logs_all AS
        {' UNION ALL '.join(union_parts)}
        ORDER BY created_at DESC;
        """
        session.execute(text(view_sql))
        session.commit()
        self.log(f"合并视图已创建: audit_logs_all (包含 {len(partitions)} 个分表)")

    def archive_month(self, year: int, month: int, compress: bool = True):
        """归档指定月份的审计日志到分表"""
        self.log(f"归档 {year}-{month:02d} 审计日志...")

        session = get_session()
        partition_name = self.get_partition_name(year, month)

        # 确保分表存在
        self.create_partition_table(partition_name, session)

        # 计算时间范围
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # 复制数据到分表
        insert_sql = f"""
        INSERT INTO {partition_name} (table_name, record_id, action, old_values, new_values, operator, ip, created_at)
        SELECT table_name, record_id, action, old_values, new_values, operator, ip, created_at
        FROM audit_logs
        WHERE created_at >= :start AND created_at < :end
        """
        result = session.execute(text(insert_sql), {"start": start_date, "end": end_date})
        inserted = result.rowcount
        self.log(f"  复制到分表: {inserted} 条")

        # 从主表删除已归档数据
        delete_sql = """
        DELETE FROM audit_logs
        WHERE created_at >= :start AND created_at < :end
        """
        result = session.execute(text(delete_sql), {"start": start_date, "end": end_date})
        deleted = result.rowcount
        self.log(f"  从主表删除: {deleted} 条")

        session.commit()

        # 压缩存储（可选）
        if compress:
            self.compress_partition(partition_name)

        return inserted

    def compress_partition(self, partition_name: str):
        """压缩分表数据到 .gz 文件"""
        self.log(f"压缩分表: {partition_name}")
        session = get_session()

        # 导出为 JSON
        rows = session.execute(text(f"SELECT * FROM {partition_name}")).fetchall()
        if not rows:
            return

        cols = [
            c[0] for c in session.execute(text(f"PRAGMA table_info({partition_name})")).fetchall()
        ]
        data = [dict(zip(cols, row)) for row in rows]

        # 写入压缩文件
        json_path = self.archive_root / f"{partition_name}.json.gz"
        with gzip.open(json_path, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)

        self.log(f"  已压缩: {json_path} ({json_path.stat().st_size} bytes)")

    def cleanup_expired(self, keep_months: int = 36):
        """清理过期分表（默认保留 3 年）"""
        self.log(f"清理 {keep_months} 个月前的分表...")

        session = get_session()
        cutoff = datetime.now() - timedelta(days=keep_months * 30)
        cutoff_year = cutoff.year
        cutoff_month = cutoff.month

        inspector = inspect(session.bind)
        all_tables = inspector.get_table_names()

        cleaned = 0
        for table in all_tables:
            if table.startswith("audit_logs_"):
                try:
                    # 解析年月
                    parts = table.split("_")
                    year = int(parts[2])
                    month = int(parts[3])
                    table_date = datetime(year, month, 1)

                    if table_date < cutoff:
                        # 删除分表
                        session.execute(text(f"DROP TABLE IF EXISTS {table}"))
                        self.log(f"  已删除过期分表: {table}")
                        cleaned += 1
                except Exception as e:
                    self.log(f"  解析失败 {table}: {e}")

        session.commit()

        # 重建合并视图
        self.create_union_view()

        self.log(f"清理完成，共删除 {cleaned} 个分表")
        return cleaned

    def run_monthly_archive(self):
        """月度归档任务（归档上个月）"""
        now = datetime.now()
        if now.month == 1:
            year, month = now.year - 1, 12
        else:
            year, month = now.year, now.month - 1

        self.archive_month(year, month)
        self.create_union_view()


def main():
    parser = argparse.ArgumentParser(description="审计日志清理工具")
    parser.add_argument(
        "action", choices=["archive", "cleanup", "monthly", "view"], help="操作类型"
    )
    parser.add_argument("--year", type=int, help="年份")
    parser.add_argument("--month", type=int, help="月份")
    parser.add_argument("--keep-months", type=int, default=36, help="保留月数")
    parser.add_argument("--db-path", default="项目根目录/data/school_data.db")
    parser.add_argument("--archive-root", default="项目根目录/archives/audit")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    archive_root = Path(args.archive_root)

    if not db_path.exists():
        print(f"错误: 数据库不存在: {db_path}")
        return 1

    init_db_with_defaults()

    cleaner = AuditCleaner(db_path, archive_root, verbose=args.verbose)

    if args.action == "archive":
        if not args.year or not args.month:
            print("错误: archive 需要 --year 和 --month")
            return 1
        cleaner.archive_month(args.year, args.month)
        cleaner.create_union_view()
    elif args.action == "cleanup":
        cleaner.cleanup_expired(args.keep_months)
    elif args.action == "monthly":
        cleaner.run_monthly_archive()
    elif args.action == "view":
        cleaner.create_union_view()

    return 0


if __name__ == "__main__":
    sys.exit(main())
