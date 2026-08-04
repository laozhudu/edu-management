"""
归档脚本测试（Sprint 3.7.19）
覆盖：verify_archive 校验、list_archives 列表、完整归档流程（monkeypatch session）
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from edu_system.models import AcademicYear, Base, Semester, SemesterStatus


@pytest.fixture
def tmp_db(tmp_path):
    """临时 SQLite DB 文件"""
    db_path = tmp_path / "school_data.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    # 建学年 + 学期
    ay = AcademicYear(name="2025-2026", sort_order=1)
    s.add(ay)
    s.commit()
    sem = Semester(
        label="2025-2026学年度第一学期",
        year_start=2025,
        semester="1",
        academic_year_id=ay.id,
        status=SemesterStatus.active,
        is_active=True,
    )
    s.add(sem)
    s.commit()
    sem_id = sem.id
    s.close()
    return db_path, sem_id, tmp_path


class TestVerifyArchive:
    def test_verify_ok(self, tmp_db, tmp_path):
        from archive_semester import SemesterArchiver

        db_path, sem_id, root = tmp_db
        archiver = SemesterArchiver(db_path, root / "archives")
        archive_dir = root / "archives" / "test_archive"
        archive_dir.mkdir(parents=True)
        # 复制 DB + 写元数据
        import shutil

        shutil.copy2(db_path, archive_dir / "school_data.db")
        sha = archiver.sha256_file(archive_dir / "school_data.db")
        size = (archive_dir / "school_data.db").stat().st_size
        with open(archive_dir / "metadata.json", "w") as f:
            json.dump({"db_sha256": sha, "db_size": size}, f)

        assert archiver.verify_archive(archive_dir) is True

    def test_verify_missing_files(self, tmp_db, tmp_path):
        from archive_semester import SemesterArchiver

        db_path, sem_id, root = tmp_db
        archiver = SemesterArchiver(db_path, root / "archives")
        empty = root / "archives" / "empty"
        empty.mkdir(parents=True)
        assert archiver.verify_archive(empty) is False

    def test_verify_sha_mismatch(self, tmp_db, tmp_path):
        from archive_semester import SemesterArchiver

        db_path, sem_id, root = tmp_db
        archiver = SemesterArchiver(db_path, root / "archives")
        archive_dir = root / "archives" / "bad"
        archive_dir.mkdir(parents=True)
        import shutil

        shutil.copy2(db_path, archive_dir / "school_data.db")
        with open(archive_dir / "metadata.json", "w") as f:
            json.dump({"db_sha256": "deadbeef", "db_size": 1}, f)
        assert archiver.verify_archive(archive_dir) is False


class TestListArchives:
    def test_list_empty(self, tmp_db, tmp_path):
        from archive_semester import SemesterArchiver

        db_path, sem_id, root = tmp_db
        archiver = SemesterArchiver(db_path, root / "archives")
        assert archiver.list_archives() == []

    def test_list_with_archives(self, tmp_db, tmp_path):
        from archive_semester import SemesterArchiver

        db_path, sem_id, root = tmp_db
        archiver = SemesterArchiver(db_path, root / "archives")
        d = root / "archives" / "school_data_2025_1_20260101"
        d.mkdir(parents=True)
        with open(d / "metadata.json", "w") as f:
            json.dump(
                {
                    "semester_label": "2025-2026学年度第一学期",
                    "archived_at": "2026-01-01",
                    "db_size": 1024,
                },
                f,
            )
        archives = archiver.list_archives()
        assert len(archives) == 1
        assert archives[0]["semester_label"] == "2025-2026学年度第一学期"


class TestArchiveFlow:
    def test_full_archive(self, tmp_db, tmp_path, monkeypatch):
        """完整归档：复制+元数据+置 archived（monkeypatch 隔离 session）"""
        from archive_semester import SemesterArchiver

        db_path, sem_id, root = tmp_db
        archiver = SemesterArchiver(db_path, root / "archives")

        # 注入临时库 session
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)

        def fake_get_session():
            return Session()

        monkeypatch.setattr("archive_semester.get_session", fake_get_session)

        result = archiver.archive_semester(sem_id)
        assert result is True

        # 验证归档目录 + 元数据
        dirs = [d for d in (root / "archives").iterdir() if d.is_dir()]
        assert len(dirs) == 1
        meta_path = dirs[0] / "metadata.json"
        assert meta_path.exists()
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["semester_id"] == sem_id
        assert meta["db_sha256"]

        # 验证原库学期状态
        s = Session()
        sem = s.query(Semester).get(sem_id)
        assert sem.status == SemesterStatus.archived
        assert sem.is_active is False
        s.close()

    def test_archive_unknown_semester(self, tmp_db, tmp_path, monkeypatch):
        from archive_semester import SemesterArchiver

        db_path, sem_id, root = tmp_db
        archiver = SemesterArchiver(db_path, root / "archives")
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)

        def _session():
            return Session()

        monkeypatch.setattr("archive_semester.get_session", _session)
        with pytest.raises(ValueError, match="不存在"):
            archiver.archive_semester(99999)
