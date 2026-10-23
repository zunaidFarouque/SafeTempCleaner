import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure src directory is in sys.path
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from prefect import flow, get_run_logger
from prefect.artifacts import create_markdown_artifact
from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import ArtifactUpdate


from common import format_time_ago, get_storage_metrics


def _get_logger() -> Any:
    """Retrieve the Prefect run logger if within a flow context, else standard logger."""
    try:
        return get_run_logger()
    except Exception:
        return logging.getLogger("prefect.temp_cleanup")


def format_bytes(byte_count: float) -> str:
    """Format bytes into a human-readable string (B, KB, MB, GB, TB)."""
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(max(0.0, byte_count))
    unit_idx = 0
    while val >= 1024.0 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1
    if unit_idx == 0:
        return f"{int(val)} B"
    return f"{val:.2f} {units[unit_idx]}"


def execute_cleanup_cycle(
    target_path: Path,
    min_age_seconds: float,
) -> Dict[str, Any]:
    """Scans target_path and deletes files/empty folders older than min_age_seconds.

    Gracefully skips any items that are locked or in use.
    """
    logger = _get_logger()

    if not target_path.exists():
        logger.warning(f"Target temp directory does not exist: {target_path}")
        return {
            "bytes_cleared": 0,
            "files_deleted": 0,
            "files_skipped": 0,
            "files_retained": 0,
            "dirs_deleted": 0,
        }

    bytes_cleared = 0
    files_deleted = 0
    files_skipped = 0
    files_retained = 0
    dirs_deleted = 0

    now = time.time()

    # Traverse bottom-up so empty subdirectories can be safely identified and removed
    for root, dirs, files in os.walk(target_path, topdown=False):
        # 1. Process files
        for file_name in files:
            file_path = Path(root) / file_name
            try:
                st = file_path.stat()
            except (OSError, FileNotFoundError):
                continue

            file_age = now - max(st.st_mtime, st.st_ctime)
            if file_age >= min_age_seconds:
                file_size = st.st_size
                try:
                    file_path.unlink()
                    bytes_cleared += file_size
                    files_deleted += 1
                except (PermissionError, OSError) as err:
                    files_skipped += 1
                    logger.debug(f"Skipping locked file {file_path.name}: {err}")
            else:
                files_retained += 1

        # 2. Process subdirectories (never remove target_path itself)
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            if dir_path.resolve() == target_path.resolve():
                continue

            try:
                st = dir_path.stat()
                dir_age = now - max(st.st_mtime, st.st_ctime)
                if dir_age >= min_age_seconds:
                    dir_path.rmdir()
                    dirs_deleted += 1
            except (PermissionError, OSError):
                pass

    logger.info(
        f"Cycle completed: Cleared {format_bytes(bytes_cleared)} across "
        f"{files_deleted} files, {dirs_deleted} dirs removed, {files_skipped} skipped/locked, "
        f"{files_retained} retained (< age threshold)."
    )

    return {
        "bytes_cleared": bytes_cleared,
        "files_deleted": files_deleted,
        "files_skipped": files_skipped,
        "files_retained": files_retained,
        "dirs_deleted": dirs_deleted,
    }


def render_cleanup_markdown(
    target_path: Path,
    min_age_hours: float,
    interval_minutes: float,
    iteration: int,
    bytes_cleared_last: float,
    total_bytes_cleared: float,
    files_deleted_last: int,
    files_skipped_last: int,
    files_retained_last: int,
    dirs_deleted_last: int,
    last_run_time: float,
    next_run_time: Any = None,
) -> str:
    """Renders the Markdown dashboard summary table for the cleanup artifact."""
    storage = get_storage_metrics(target_path)
    drive_label = target_path.anchor if target_path.anchor else str(target_path)

    last_run_display = format_time_ago(last_run_time)
    if next_run_time:
        next_dt = datetime.fromtimestamp(next_run_time)
        next_run_display = f"`{next_dt.strftime('%Y-%m-%d %I:%M:%S %p')}`"
    else:
        next_run_display = "*Completed / Run Once*"

    markdown = f"""# 🧹 Temp Directory Cleanup Dashboard

**Target Directory**: `{target_path}`  
**Age Threshold**: `{min_age_hours} hours` | **Cycle Frequency**: `Every {interval_minutes} minutes`

---

## 📊 Summary Metrics

| Metric | Value |
| :--- | :--- |
| **Space Cleared (Last Iteration)** | **`{format_bytes(bytes_cleared_last)}`** (`{bytes_cleared_last:,} bytes`) |
| **Total Space Cleared (Lifetime / Run)** | **`{format_bytes(total_bytes_cleared)}`** (`{total_bytes_cleared:,} bytes`) |
| **Run Iteration Count** | **`{iteration}`** |
| **Last Run Completed** | {last_run_display} |
| **Next Run Scheduled** | {next_run_display} |
| **Files Cleared (Last Iteration)** | `{files_deleted_last}` files |
| **Files Skipped / In-Use (Last Iteration)** | `{files_skipped_last}` files |
| **Files Retained (< Age Threshold)** | `{files_retained_last}` files |
| **Empty Folders Removed (Last Iteration)** | `{dirs_deleted_last}` dirs |

---

## 💾 Storage Health (`{drive_label}`)
- **Free Space**: `{storage['free_gb']:.2f} GB` / `{storage['total_gb']:.2f} GB` ({storage['badge']})
- **Disk Usage**: `{storage['used_pct']:.1f}%`

---
*Status: Active | Last Updated: `{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}`*
"""
    return markdown




def publish_cleanup_artifact(
    artifact_key: str,
    markdown_content: str,
    iteration: int,
    existing_artifact_id: Optional[str] = None,
    logger: Optional[Any] = None,
) -> Optional[str]:
    """Creates or updates the Prefect markdown artifact card in-place."""
    desc = f"Temp directory cleanup status (Iteration #{iteration})"
    artifact_id = existing_artifact_id

    if artifact_id:
        try:
            client = get_client(sync_client=True)
            client.update_artifact(
                artifact_id=artifact_id,
                artifact=ArtifactUpdate(
                    data=markdown_content,
                    description=desc,
                ),
            )
            return artifact_id
        except Exception as update_err:
            if logger:
                logger.debug(f"In-place artifact update failed, will recreate: {update_err}")

    try:
        new_id = create_markdown_artifact(
            key=artifact_key,
            markdown=markdown_content,
            description=desc,
        )
        return str(new_id)
    except Exception as create_err:
        if logger:
            logger.warning(f"Failed to publish cleanup artifact: {create_err}")
        return artifact_id



@flow(name="temp-cleanup-flow")
def temp_cleanup_flow(
    temp_dir: str = r"C:\Users\mfarouque2026\AppData\Local\Temp",
    min_age_hours: float = 2.0,
    interval_minutes: float = 30.0,
    run_once: bool = False,
    artifact_key: str = "temp-cleanup-dashboard",
) -> Dict[str, Any]:
    """Continuous cleanup flow that periodically purges old items from temp_dir."""
    logger = _get_logger()
    target_path = Path(temp_dir).resolve()
    min_age_seconds = min_age_hours * 3600.0
    sleep_interval_seconds = interval_minutes * 60.0

    logger.info("=" * 60)
    logger.info("  Starting Temp Directory Cleanup Flow")
    logger.info(f"  Target: {target_path}")
    logger.info(f"  Min Age: {min_age_hours} hours ({min_age_seconds:,.0f}s)")
    logger.info(f"  Interval: {interval_minutes} minutes")
    logger.info(f"  Run Once: {run_once}")
    logger.info("=" * 60)

    iteration = 0
    total_bytes_cleared = 0.0
    artifact_id: Optional[str] = None

    while True:
        iteration += 1
        cycle_start_time = time.time()
        logger.info(f"--- Starting Cleanup Iteration #{iteration} ---")

        cycle_result = execute_cleanup_cycle(
            target_path=target_path,
            min_age_seconds=min_age_seconds,
        )

        bytes_cleared_last = float(cycle_result["bytes_cleared"])
        total_bytes_cleared += bytes_cleared_last

        cycle_end_time = time.time()
        next_run_time = (cycle_end_time + sleep_interval_seconds) if not run_once else None

        markdown_content = render_cleanup_markdown(
            target_path=target_path,
            min_age_hours=min_age_hours,
            interval_minutes=interval_minutes,
            iteration=iteration,
            bytes_cleared_last=bytes_cleared_last,
            total_bytes_cleared=total_bytes_cleared,
            files_deleted_last=cycle_result["files_deleted"],
            files_skipped_last=cycle_result["files_skipped"],
            files_retained_last=cycle_result["files_retained"],
            dirs_deleted_last=cycle_result["dirs_deleted"],
            last_run_time=cycle_end_time,
            next_run_time=next_run_time,
        )

        artifact_id = publish_cleanup_artifact(
            artifact_key=artifact_key,
            markdown_content=markdown_content,
            iteration=iteration,
            existing_artifact_id=artifact_id,
            logger=logger,
        )

        if run_once:
            logger.info("run_once=True: Cleanup complete. Exiting flow.")
            break

        logger.info(
            f"Iteration #{iteration} complete. Sleeping for {interval_minutes} minutes "
            f"(next run around {datetime.fromtimestamp(next_run_time).strftime('%I:%M:%S %p')})..."
        )
        time.sleep(sleep_interval_seconds)

    return {
        "iterations": iteration,
        "total_bytes_cleared": total_bytes_cleared,
        "last_iteration_bytes": bytes_cleared_last,
    }


if __name__ == "__main__":
    temp_cleanup_flow(
        temp_dir=r"C:\Users\mfarouque2026\AppData\Local\Temp",
        min_age_hours=2.0,
        interval_minutes=30.0,
        run_once=False,
    )
