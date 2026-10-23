import os
import time
from pathlib import Path
from src.config.models import PathRule
from src.core.cleaner import clean_path, match_file_patterns


def test_match_file_patterns():
    assert match_file_patterns("test.tmp", ["*"]) is True
    assert match_file_patterns("test.tmp", ["*.tmp"]) is True
    assert match_file_patterns("test.log", ["*.tmp"]) is False
    assert match_file_patterns("test.log", ["*.tmp", "*.log"]) is True
    assert match_file_patterns("ANYTHING", ["*"]) is True


def test_clean_path_nonexistent():
    rule = PathRule(
        path="C:/non_existent_folder_xyz_12345",
        min_age_hours=2.0,
    )
    result = clean_path(rule)
    assert result.bytes_cleared == 0
    assert result.files_deleted == 0
    assert result.files_skipped == 0
    assert result.files_retained == 0
    assert result.dirs_deleted == 0


def test_clean_path_old_and_new_files(tmp_path, monkeypatch):
    old_file = tmp_path / "old.tmp"
    old_file.write_bytes(b"A" * 100)

    new_file = tmp_path / "new.tmp"
    new_file.write_bytes(b"B" * 50)

    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    old_nested = sub_dir / "old_nested.log"
    old_nested.write_bytes(b"C" * 200)

    three_hours_ago = time.time() - (3 * 3600)
    real_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if "old" in self.name or self.name == "sub":
            return os.stat_result(
                (
                    st.st_mode,
                    st.st_ino,
                    st.st_dev,
                    st.st_nlink,
                    st.st_uid,
                    st.st_gid,
                    st.st_size,
                    three_hours_ago,  # atime
                    three_hours_ago,  # mtime
                    three_hours_ago,  # ctime
                )
            )
        return st

    monkeypatch.setattr(Path, "stat", mock_stat)

    rule = PathRule(
        path=str(tmp_path),
        min_age_hours=2.0,
        file_patterns=["*"],
        prune_empty_dirs=True,
    )

    result = clean_path(rule)
    assert result.bytes_cleared == 300
    assert result.files_deleted == 2
    assert result.files_retained == 1
    assert result.dirs_deleted == 1
    assert not old_file.exists()
    assert not old_nested.exists()
    assert not sub_dir.exists()
    assert new_file.exists()
    assert tmp_path.exists()


def test_clean_path_handles_locked_files(tmp_path, monkeypatch):
    locked = tmp_path / "locked.tmp"
    locked.write_bytes(b"LOCKED" * 20)

    three_hours_ago = time.time() - (3 * 3600)
    real_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if self.name == "locked.tmp":
            return os.stat_result(
                (
                    st.st_mode,
                    st.st_ino,
                    st.st_dev,
                    st.st_nlink,
                    st.st_uid,
                    st.st_gid,
                    st.st_size,
                    three_hours_ago,
                    three_hours_ago,
                    three_hours_ago,
                )
            )
        return st

    original_unlink = Path.unlink

    def mock_unlink(self, *args, **kwargs):
        if self.name == "locked.tmp":
            raise PermissionError("Access is denied (file locked by ArcGIS)")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", mock_stat)
    monkeypatch.setattr(Path, "unlink", mock_unlink)

    rule = PathRule(path=str(tmp_path), min_age_hours=2.0)
    result = clean_path(rule)

    assert result.files_skipped == 1
    assert result.files_deleted == 0
    assert result.bytes_cleared == 0
    assert locked.exists()
