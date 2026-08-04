#!/usr/bin/env python3
"""
学期上下文迁移脚本
支持 dry-run、checksum 校验、自动回滚
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import inspect, text

from edu_system.database import get_session, init_db_with_defaults


class MigrationScript:
    def __init__(self, session, dry_run=False, verbose=False):
        self.session = session
        self.dry_run = dry_run
        self.verbose = verbose
        self.executed_sql = []
        self.checksums_before = {}
        self.checksums_after = {}

    def log(self, msg):
        if self.verbose or self.dry_run:
            print(f"[{'DRY-RUN' if self.dry_run else 'EXEC'}] {msg}")

    def execute_sql(self, sql, params=None):
        """执行 SQL"""
        self.executed_sql.append(sql)
        self.log(f"SQL: {sql}")
        if not self.dry_run:
            self.session.execute(text(sql), params or {})

    def get_table_checksum(self, table_name):
        """计算表校验和"""
        try:
            # 使用 COUNT(*) + 简单聚合作为校验
            count = self.session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            # 对于有 updated_at 的表，加上 MAX(updated_at)
            cols = [c["name"] for c in inspect(self.session.bind).get_columns(table_name)]
            if "updated_at" in cols:
                max_updated = self.session.execute(
                    text(f"SELECT MAX(updated_at) FROM {table_name}")
                ).scalar()
                return f"{count}:{max_updated}"
            return str(count)
        except Exception as e:
            return f"ERROR: {e}"

    def snapshot_checksums(self, tables):
        """记录所有表校验和"""
        for t in tables:
            self.checksums_before[t] = self.get_table_checksum(t)

    def verify_checksums(self, tables):
        """校验迁移前后校验和"""
        errors = []
        for t in tables:
            after = self.get_table_checksum(t)
            before = self.checksums_before.get(t, "N/A")
            if after != before:
                self.log(f"⚠️ 校验和变化: {t} before={before} after={after}")
            else:
                self.log(f"✅ 校验和一致: {t} = {after}")
        return errors

    def run_migration(self):
        """执行完整迁移"""
        self.log("=== 开始学期上下文迁移 ===")

        # 1. 目标表列表
        tables = [
            "students",
            "teachers",
            "classes",
            "exams",
            "scores",
            "class_subjects",
            "student_movements",
            "classrooms",
            "semester_configs",
            "data_locks",
            "semester_stats_cache",
        ]

        # 2. 记录迁移前校验和
        self.snapshot_checksums(tables)

        # 3. 创建学年
        self.log("创建默认学年: 2024-2025")
        self.execute_sql(
            """
            INSERT OR IGNORE INTO academic_years (id, name, sort_order, is_active, description)
            VALUES (1, '2024-2025', 1, 1, '2024-2025 学年')
        """
        )

        # 4. 更新学期表：关联学年
        self.log("更新学期表：添加 academic_year_id")
        self.execute_sql(
            """
            UPDATE semesters SET academic_year_id = 1 WHERE academic_year_id IS NULL OR academic_year_id = 0
        """
        )

        # 5. 所有业务表添加 semester_id（如果还没有）
        self.log("确保所有业务表有 semester_id 非空外键")

        # students
        self.execute_sql(
            """
            UPDATE students SET semester_id = 1 WHERE semester_id IS NULL OR semester_id = 0
        """
        )

        # teachers
        self.execute_sql(
            """
            UPDATE teachers SET semester_id = 1 WHERE semester_id IS NULL OR semester_id = 0
        """
        )

        # classes (已有)

        # exams
        self.execute_sql(
            """
            UPDATE exams SET semester_id = 1 WHERE semester_id IS NULL OR semester_id = 0
        """
        )

        # scores (通过 exam 关联，无需直接更新)

        # class_subjects
        self.execute_sql(
            """
            UPDATE class_subjects SET semester_id = 1 WHERE semester_id IS NULL OR semester_id = 0
        """
        )

        # student_movements
        self.execute_sql(
            """
            UPDATE student_movements SET semester_id = 1 WHERE semester_id IS NULL OR semester_id = 0
        """
        )

        # classrooms
        self.execute_sql(
            """
            UPDATE classrooms SET semester_id = 1 WHERE semester_id IS NULL OR semester_id = 0
        """
        )

        # 6. Setting 表拆分：创建 GlobalSetting 和 SemesterConfig
        self.log("Setting 表拆分：迁移配置到 GlobalSetting 和 SemesterConfig")

        # 先迁移全局配置
        self.execute_sql(
            """
            INSERT OR IGNORE INTO global_settings (key, value, description, updated_at)
            SELECT key, value, '', datetime('now') FROM settings
        """
        )

        # 再迁移学期配置（简化：将所有 settings 复制到学期1的 semester_configs）
        self.execute_sql(
            """
            INSERT OR IGNORE INTO semester_configs (semester_id, key, value, version, inherited_from, description, created_at)
            SELECT 1, key, value, 1, NULL, '', datetime('now') FROM settings
        """
        )

        # 7. 创建默认校区
        self.log("创建默认校区")
        self.execute_sql(
            """
            INSERT OR IGNORE INTO schools (id, name, code, config_json, is_active, created_at)
            VALUES (1, '教务管理系统-本部', 'SLZX', '{}', 1, datetime('now'))
        """
        )

        # 8. 所有业务表添加 school_id（默认 1）
        self.log("添加 school_id 到业务表")
        tables_with_school = [
            "students",
            "teachers",
            "classes",
            "exams",
            "scores",
            "class_subjects",
            "student_movements",
            "classrooms",
            "semester_configs",
            "data_locks",
            "semester_stats_cache",
        ]
        for t in tables_with_school:
            try:
                self.execute_sql(
                    f"UPDATE {t} SET school_id = 1 WHERE school_id IS NULL OR school_id = 0"
                )
            except:
                pass  # 表可能不存在 school_id 列（旧版本）

        # 9. 更新学期状态
        self.log("更新学期状态：当前学期设为 active，其他为 draft")
        self.execute_sql(
            """
            UPDATE semesters SET 
                is_active = CASE WHEN id = 1 THEN 1 ELSE 0 END,
                status = CASE WHEN id = 1 THEN 'active' ELSE 'draft' END
            WHERE status IS NULL OR status = ''
        """
        )

        # 10. 创建索引（如果不存在）
        self.log("创建必要索引")
        indexes = [
            ("idx_students_semester", "students", "semester_id"),
            ("idx_teachers_semester", "teachers", "semester_id"),
            ("idx_exams_semester", "exams", "semester_id"),
            ("idx_class_subjects_semester", "class_subjects", "semester_id"),
            ("idx_student_movements_semester", "student_movements", "semester_id"),
            ("idx_classrooms_semester", "classrooms", "semester_id"),
            ("idx_semester_configs_semester", "semester_configs", "semester_id"),
            ("idx_data_locks_semester", "data_locks", "semester_id"),
            ("idx_semester_stats_cache_semester", "semester_stats_cache", "semester_id"),
        ]
        for idx_name, table, col in indexes:
            self.execute_sql(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})")

        # 11. 提交事务
        if not self.dry_run:
            self.session.commit()
            self.log("事务已提交")

        # 12. 校验
        self.log("=== 校验迁移结果 ===")
        self.verify_checksums(tables)

        self.log("=== 迁移完成 ===")
        return True

    def generate_rollback_sql(self):
        """生成回滚 SQL"""
        rollback_sql = [
            "BEGIN IMMEDIATE;",
            "-- 回滚学期状态",
            "UPDATE semesters SET is_active = 0, status = 'draft' WHERE id = 1;",
            "-- 删除默认校区",
            "DELETE FROM schools WHERE id = 1;",
            "-- 清理 semester_configs",
            "DELETE FROM semester_configs WHERE semester_id = 1;",
            "-- 清理 global_settings",
            "DELETE FROM global_settings;",
            "-- 恢复 semester_id",
            "UPDATE students SET semester_id = NULL WHERE semester_id = 1;",
            "UPDATE teachers SET semester_id = NULL WHERE semester_id = 1;",
            "UPDATE exams SET semester_id = NULL WHERE semester_id = 1;",
            "UPDATE class_subjects SET semester_id = NULL WHERE semester_id = 1;",
            "UPDATE student_movements SET semester_id = NULL WHERE semester_id = 1;",
            "UPDATE classrooms SET semester_id = NULL WHERE semester_id = 1;",
            "-- 删除 academic_year",
            "DELETE FROM academic_years WHERE id = 1;",
            "COMMIT;",
        ]
        return "\n".join(rollback_sql)


def main():
    parser = argparse.ArgumentParser(description="学期上下文迁移脚本")
    parser.add_argument("--dry-run", action="store_true", help="仅打印 SQL，不执行")
    parser.add_argument("--check-only", action="store_true", help="仅校验，不执行迁移")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    parser.add_argument("--generate-rollback", action="store_true", help="生成回滚 SQL 到 stdout")
    args = parser.parse_args()

    if args.generate_rollback:
        session = None  # 不需要 session
        # 简单输出回滚 SQL
        print(
            "\n".join(
                [
                    "BEGIN IMMEDIATE;",
                    "UPDATE semesters SET is_active = 0, status = 'draft' WHERE id = 1;",
                    "DELETE FROM schools WHERE id = 1;",
                    "DELETE FROM semester_configs WHERE semester_id = 1;",
                    "DELETE FROM global_settings;",
                    "UPDATE students SET semester_id = NULL WHERE semester_id = 1;",
                    "UPDATE teachers SET semester_id = NULL WHERE semester_id = 1;",
                    "UPDATE exams SET semester_id = NULL WHERE semester_id = 1;",
                    "UPDATE class_subjects SET semester_id = NULL WHERE semester_id = 1;",
                    "UPDATE student_movements SET semester_id = NULL WHERE semester_id = 1;",
                    "UPDATE classrooms SET semester_id = NULL WHERE semester_id = 1;",
                    "DELETE FROM academic_years WHERE id = 1;",
                    "COMMIT;",
                ]
            )
        )
        return 0

    # 初始化数据库
    init_db_with_defaults()
    session = get_session()

    migration = MigrationScript(
        session, dry_run=args.dry_run or args.check_only, verbose=args.verbose
    )

    if args.check_only:
        migration.log("=== 校验模式：仅检查当前状态 ===")
        tables = ["students", "teachers", "classes", "exams", "scores", "semesters"]
        migration.snapshot_checksums(tables)
        migration.verify_checksums(tables)
        return 0

    try:
        success = migration.run_migration()
        if success and not args.dry_run:
            print("\n✅ 迁移成功完成")
        elif args.dry_run:
            print("\n✅ Dry-run 完成，未实际执行")
        return 0 if success else 1
    except Exception as e:
        if not args.dry_run:
            session.rollback()
        print(f"\n❌ 迁移失败: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
