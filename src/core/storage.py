import os
import shutil
from pathlib import Path
from typing import Dict, Any


def get_drive_storage(drive_path: Path) -> Dict[str, Any]:
    """Retrieves drive free/used storage metrics and health status."""
    try:
        resolved = drive_path.resolve() if drive_path.exists() else drive_path
        target = resolved.anchor if resolved.anchor else str(resolved)
        total_b, used_b, free_b = shutil.disk_usage(target)
        total_gb = total_b / (1024**3)
        used_gb = used_b / (1024**3)
        free_gb = free_b / (1024**3)
        used_pct = (used_b / total_b) * 100 if total_b > 0 else 0.0

        if free_gb < 15:
            badge = "🔴 Critical (< 15 GB)"
        elif free_gb < 30:
            badge = "🟠 Caution (< 30 GB)"
        else:
            badge = "🟢 Safe (> 30 GB)"

        return {
            "drive": target,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_pct": round(used_pct, 1),
            "badge": badge,
        }
    except Exception:
        return {
            "drive": str(drive_path),
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "used_pct": 0.0,
            "badge": "⚪ Unknown",
        }


def inspect_directory_stats(dir_path: Path) -> Dict[str, int]:
    """Calculates the current number of files and total byte size within dir_path."""
    if not dir_path.exists() or not dir_path.is_dir():
        return {"file_count": 0, "total_bytes": 0}

    count = 0
    total_size = 0

    try:
        for root, _, files in os.walk(dir_path):
            for f in files:
                file_path = Path(root) / f
                try:
                    total_size += file_path.stat().st_size
                    count += 1
                except (OSError, FileNotFoundError):
                    continue
    except Exception:
        pass

    return {"file_count": count, "total_bytes": total_size}
