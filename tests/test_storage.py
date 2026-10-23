from pathlib import Path
from unittest.mock import patch
from src.core.storage import get_drive_storage, inspect_directory_stats


def test_get_drive_storage():
    with patch("shutil.disk_usage") as mock_disk:
        # 100 GB total, 60 GB used, 40 GB free
        mock_disk.return_value = (
            100 * 1024**3,
            60 * 1024**3,
            40 * 1024**3,
        )
        res = get_drive_storage(Path("C:/Temp"))
        assert res["total_gb"] == 100.0
        assert res["used_gb"] == 60.0
        assert res["free_gb"] == 40.0
        assert res["used_pct"] == 60.0
        assert "🟢" in res["badge"]


def test_get_drive_storage_critical():
    with patch("shutil.disk_usage") as mock_disk:
        # 100 GB total, 90 GB used, 10 GB free
        mock_disk.return_value = (
            100 * 1024**3,
            90 * 1024**3,
            10 * 1024**3,
        )
        res = get_drive_storage(Path("C:/Temp"))
        assert "🔴" in res["badge"]


def test_inspect_directory_stats(tmp_path):
    # Empty dir
    stats = inspect_directory_stats(tmp_path)
    assert stats["file_count"] == 0
    assert stats["total_bytes"] == 0

    # Add files
    f1 = tmp_path / "a.tmp"
    f1.write_bytes(b"A" * 100)
    sub = tmp_path / "nested"
    sub.mkdir()
    f2 = sub / "b.log"
    f2.write_bytes(b"B" * 250)

    stats = inspect_directory_stats(tmp_path)
    assert stats["file_count"] == 2
    assert stats["total_bytes"] == 350
