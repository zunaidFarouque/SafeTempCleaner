import shutil
from pathlib import Path


def get_storage_metrics(drive_path: Path) -> dict:
    """Retrieves storage statistics and health status for the target drive."""
    try:
        target = drive_path.anchor if drive_path.anchor else str(drive_path)
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
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "used_pct": used_pct,
            "badge": badge,
        }
    except Exception:
        return {
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "used_pct": 0.0,
            "badge": "⚪ Unknown",
        }
