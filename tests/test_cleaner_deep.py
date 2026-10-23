import os
import time
from pathlib import Path
from src.config.models import PathRule
from src.core.cleaner import clean_path, match_file_patterns


def test_cleaner_case_insensitive_patterns():
    assert match_file_patterns("DATA.TMP", ["*.tmp"]) is True
    assert match_file_patterns("image.PNG", ["*.png"]) is True
    assert match_file_patterns("Report.PDF", ["*.txt", "*.pdf"]) is True
    assert match_file_patterns("file.xyz", ["*.abc"]) is False


def test_cleaner_deep_nested_directory_pruning(tmp_path, monkeypatch):
    # Setup nested hierarchy: level1/level2/level3/old_nested.tmp
    l1 = tmp_path / "level1"
    l2 = l1 / "level2"
    l3 = l2 / "level3"
    l3.mkdir(parents=True)

    old_file = l3 / "old_nested.tmp"
    old_file.write_bytes(b"DATA" * 50)

    three_hours_ago = time.time() - (3 * 3600)
    real_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if "level" in self.name or "old_nested" in self.name:
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

    monkeypatch.setattr(Path, "stat", mock_stat)

    rule = PathRule(
        path=str(tmp_path),
        min_age_hours=2.0,
        file_patterns=["*"],
        prune_empty_dirs=True,
    )

    res = clean_path(rule)
    assert res.files_deleted == 1
    assert res.dirs_deleted == 3  # level3, level2, level1 all empty and pruned
    assert res.bytes_cleared == 200
    assert tmp_path.exists()  # Target root must be preserved
    assert not l1.exists()


def test_cleaner_retains_directory_if_contains_young_file(tmp_path, monkeypatch):
    folder = tmp_path / "mixed_folder"
    folder.mkdir()
    old_f = folder / "old.tmp"
    old_f.write_bytes(b"OLD" * 10)
    young_f = folder / "young.tmp"
    young_f.write_bytes(b"YOUNG" * 10)

    three_hours_ago = time.time() - (3 * 3600)
    real_stat = Path.stat

    def mock_stat(self, *args, **kwargs):
        st = real_stat(self, *args, **kwargs)
        if "old" in self.name or self.name == "mixed_folder":
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

    monkeypatch.setattr(Path, "stat", mock_stat)

    rule = PathRule(
        path=str(tmp_path),
        min_age_hours=2.0,
        file_patterns=["*"],
        prune_empty_dirs=True,
    )

    res = clean_path(rule)
    assert res.files_deleted == 1
    assert res.files_retained == 1
    assert res.dirs_deleted == 0  # Not deleted because young_f remains!
    assert folder.exists()
    assert young_f.exists()
    assert not old_f.exists()
