import os
import time
import fnmatch
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.config.models import PathRule

logger = logging.getLogger("SafeTempCleaner.cleaner")


@dataclass
class CleanupResult:
    """Statistics returned from a single cleanup cycle."""
    rule_id: str
    path: str
    bytes_cleared: int = 0
    files_deleted: int = 0
    files_skipped: int = 0
    files_retained: int = 0
    dirs_deleted: int = 0
    duration_seconds: float = 0.0
    timestamp: float = 0.0


def match_file_patterns(filename: str, patterns: List[str]) -> bool:
    """Checks if a filename matches any of the glob patterns."""
    if not patterns or "*" in patterns:
        return True
    for pat in patterns:
        pat = pat.strip()
        if not pat:
            continue
        if fnmatch.fnmatch(filename.lower(), pat.lower()):
            return True
    return False


def clean_path(rule: PathRule) -> CleanupResult:
    """
    Safely executes a cleanup cycle for a given PathRule.
    - Files older than min_age_hours matching file_patterns are deleted permanently.
    - Locked or in-use files (PermissionError/OSError) are skipped gracefully.
    - Subdirectories that become empty and older than min_age_hours are removed.
    - Target root directory itself is never removed.
    """
    start_time = time.time()
    result = CleanupResult(
        rule_id=rule.id,
        path=rule.path,
        timestamp=start_time,
    )

    target_path = Path(rule.path)
    if not target_path.exists():
        logger.warning(f"Target path does not exist: {rule.path}")
        result.duration_seconds = time.time() - start_time
        return result

    min_age_seconds = rule.min_age_hours * 3600.0
    now = time.time()

    # Traverse bottom-up so empty subdirectories can be cleanly removed
    try:
        for root, dirs, files in os.walk(target_path, topdown=False):
            # 1. Process files in current directory
            for file_name in files:
                if not match_file_patterns(file_name, rule.file_patterns):
                    continue

                file_path = Path(root) / file_name
                try:
                    st = file_path.stat()
                except (OSError, FileNotFoundError):
                    continue

                # Use max of mtime and ctime (most recent file modification or creation activity)
                file_age = now - max(st.st_mtime, st.st_ctime)
                if file_age >= min_age_seconds:
                    file_size = st.st_size
                    try:
                        file_path.unlink()
                        result.bytes_cleared += file_size
                        result.files_deleted += 1
                    except (PermissionError, OSError) as err:
                        result.files_skipped += 1
                        logger.debug(f"Skipping in-use/locked file {file_path.name}: {err}")
                else:
                    result.files_retained += 1

            # 2. Process subdirectories (never remove the target root itself)
            if rule.prune_empty_dirs:
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    if dir_path.resolve() == target_path.resolve():
                        continue

                    try:
                        st = dir_path.stat()
                        dir_age = now - max(st.st_mtime, st.st_ctime)
                        if dir_age >= min_age_seconds:
                            dir_path.rmdir()  # Fails safely if directory is not empty
                            result.dirs_deleted += 1
                    except (PermissionError, OSError):
                        pass
    except Exception as err:
        logger.error(f"Error during scan of {rule.path}: {err}")

    result.duration_seconds = time.time() - start_time
    logger.info(
        f"Completed [{rule.path}]: Cleared {result.bytes_cleared} bytes across "
        f"{result.files_deleted} files, {result.dirs_deleted} dirs removed, "
        f"{result.files_skipped} locked/skipped, {result.files_retained} retained."
    )
    return result
