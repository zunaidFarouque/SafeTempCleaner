from datetime import datetime
from typing import Optional


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


def format_time_ago(timestamp: Optional[float], current_time: Optional[float] = None) -> str:
    """Formats a timestamp into 'YYYY-MM-DD hh:mm:ss AM/PM (Xm Ys ago)' or 'Never'."""
    if timestamp is None or timestamp <= 0:
        return "Never"

    now = current_time if current_time is not None else datetime.now().timestamp()
    exact_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %I:%M:%S %p")
    diff_seconds = max(0.0, now - timestamp)

    if diff_seconds < 60:
        ago_str = f"{int(diff_seconds)}s ago"
    elif diff_seconds < 3600:
        mins = int(diff_seconds // 60)
        secs = int(diff_seconds % 60)
        ago_str = f"{mins}m {secs}s ago"
    elif diff_seconds < 86400:
        hours = int(diff_seconds // 3600)
        mins = int((diff_seconds % 3600) // 60)
        ago_str = f"{hours}h {mins}m ago"
    else:
        days = int(diff_seconds // 86400)
        hours = int((diff_seconds % 86400) // 3600)
        ago_str = f"{days}d {hours}h ago"

    return f"{exact_str} ({ago_str})"


def format_duration(seconds: float) -> str:
    """Formats seconds into human-readable compact string like '1d 1h', '1h 1m', '2m', '45s'."""
    if seconds <= 0:
        return "0s"
    total_seconds = int(seconds)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 and len(parts) < 2:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
