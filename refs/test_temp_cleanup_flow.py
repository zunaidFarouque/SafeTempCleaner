import os
import sys
import time
from pathlib import Path
import pytest

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(repo_root / "src") not in sys.path:
    sys.path.insert(0, str(repo_root / "src"))

from Management.temp_cleanup_flow import (
    execute_cleanup_cycle,
    format_bytes,
    publish_cleanup_artifact,
    render_cleanup_markdown,
    temp_cleanup_flow,
)


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024 * 1024 * 2.5) == "2.50 MB"
    assert format_bytes(1024 * 1024 * 1024 * 4.75) == "4.75 GB"
    assert format_bytes(1024 * 1024 * 1024 * 1024 * 1.5) == "1.50 TB"


def test_execute_cleanup_cycle_nonexistent_directory(tmp_path):
    missing_dir = tmp_path / "does_not_exist"
    result = execute_cleanup_cycle(target_path=missing_dir, min_age_seconds=7200)
    assert result == {
        "bytes_cleared": 0,
        "files_deleted": 0,
        "files_skipped": 0,
        "files_retained": 0,
        "dirs_deleted": 0,
    }


def test_execute_cleanup_cycle_old_and_new_files(tmp_path, monkeypatch):
    old_file = tmp_path / "old_test.tmp"
    old_file.write_bytes(b"A" * 100)

    new_file = tmp_path / "new_test.tmp"
    new_file.write_bytes(b"B" * 50)

    sub_dir = tmp_path / "sub_folder"
    sub_dir.mkdir()
    old_nested = sub_dir / "old_nested.log"
    old_nested.write_bytes(b"C" * 200)

    three_hours_ago = time.time() - (3 * 3600)
    real_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if "old" in self.name or self.name == "sub_folder":
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

    result = execute_cleanup_cycle(target_path=tmp_path, min_age_seconds=7200)

    assert result["bytes_cleared"] == 300  # 100 + 200
    assert result["files_deleted"] == 2
    assert result["files_retained"] == 1
    assert not old_file.exists()
    assert not old_nested.exists()
    assert not sub_dir.exists()
    assert new_file.exists()
    assert tmp_path.exists()


def test_execute_cleanup_cycle_handles_locked_files(tmp_path, monkeypatch):
    locked_file = tmp_path / "locked.tmp"
    locked_file.write_bytes(b"LOCKED" * 10)

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
            raise PermissionError("File in use by another process")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", mock_stat)
    monkeypatch.setattr(Path, "unlink", mock_unlink)

    result = execute_cleanup_cycle(target_path=tmp_path, min_age_seconds=7200)

    assert result["files_skipped"] == 1
    assert result["files_deleted"] == 0
    assert result["bytes_cleared"] == 0
    assert locked_file.exists()


def test_render_cleanup_markdown(tmp_path):
    md = render_cleanup_markdown(
        target_path=tmp_path,
        min_age_hours=2.0,
        interval_minutes=30.0,
        iteration=3,
        bytes_cleared_last=1048576,
        total_bytes_cleared=3145728,
        files_deleted_last=12,
        files_skipped_last=2,
        files_retained_last=45,
        dirs_deleted_last=3,
        last_run_time=time.time() - 60,
        next_run_time=time.time() + 1740,
    )

    assert "Temp Directory Cleanup Dashboard" in md
    assert "Space Cleared (Last Iteration)" in md
    assert "1.00 MB" in md
    assert "Total Space Cleared (Lifetime / Run)" in md
    assert "3.00 MB" in md
    assert "Run Iteration Count" in md
    assert "3" in md
    assert "Next Run Scheduled" in md
    assert "Files Cleared (Last Iteration)" in md
    assert "12" in md
    assert "Files Skipped / In-Use (Last Iteration)" in md
    assert "2" in md


def test_publish_cleanup_artifact():
    from unittest.mock import MagicMock, patch
    with patch("Management.temp_cleanup_flow.create_markdown_artifact") as mock_create, \
         patch("Management.temp_cleanup_flow.get_client") as mock_client_factory:
        mock_create.return_value = "new-artifact-id-123"

        # Case 1: First creation
        art_id = publish_cleanup_artifact(
            artifact_key="test-key",
            markdown_content="# Test",
            iteration=1,
            existing_artifact_id=None,
        )
        assert art_id == "new-artifact-id-123"
        mock_create.assert_called_once()

        # Case 2: Update existing artifact
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        updated_id = publish_cleanup_artifact(
            artifact_key="test-key",
            markdown_content="# Updated Test",
            iteration=2,
            existing_artifact_id="new-artifact-id-123",
        )
        assert updated_id == "new-artifact-id-123"
        mock_client.update_artifact.assert_called_once()


def test_temp_cleanup_flow_run_once(tmp_path, monkeypatch):
    from unittest.mock import patch
    test_file = tmp_path / "old.tmp"
    test_file.write_bytes(b"X" * 500)
    old_time = time.time() - 10000

    real_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if self.name == "old.tmp":
            return os.stat_result(
                (
                    st.st_mode,
                    st.st_ino,
                    st.st_dev,
                    st.st_nlink,
                    st.st_uid,
                    st.st_gid,
                    st.st_size,
                    old_time,
                    old_time,
                    old_time,
                )
            )
        return st

    monkeypatch.setattr(Path, "stat", mock_stat)

    with patch("Management.temp_cleanup_flow.publish_cleanup_artifact") as mock_publish:
        mock_publish.return_value = "mock-id"
        result = temp_cleanup_flow.fn(
            temp_dir=str(tmp_path),
            min_age_hours=2.0,
            interval_minutes=30.0,
            run_once=True,
        )

    assert result["iterations"] == 1
    assert result["total_bytes_cleared"] == 500
    assert not test_file.exists()


def test_submit_temp_cleanup_success():
    from unittest.mock import patch
    from Management.submit_temp_cleanup import submit

    with patch("Management.submit_temp_cleanup.temp_cleanup_flow") as mock_flow:
        submit()
        mock_flow.assert_called_once()


def test_submit_temp_cleanup_failure():
    from unittest.mock import patch
    from Management.submit_temp_cleanup import submit

    with patch("Management.submit_temp_cleanup.temp_cleanup_flow", side_effect=RuntimeError("Flow error")):
        with pytest.raises(SystemExit) as exc_info:
            submit()
        assert exc_info.value.code == 1
