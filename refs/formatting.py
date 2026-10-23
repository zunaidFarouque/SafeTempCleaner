import re
from datetime import datetime, timedelta


def format_time_ago(timestamp: float | None, current_time: float | None = None) -> str:
    """Formats a timestamp into '`YYYY-MM-DD hh:mm:ss AM/PM` (Xm Ys ago)'."""
    if timestamp is None or timestamp <= 0:
        return "None yet"

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

    return f"`{exact_str}` ({ago_str})"


def sanitize_artifact_key(name: str, prefix: str = "") -> str:
    """Converts a pipeline name to a valid Prefect artifact key (lowercase alphanumeric and dashes)."""
    sanitized = re.sub(r"[^a-z0-9\-]", "-", name.lower())
    sanitized = re.sub(r"-+", "-", sanitized).strip("-")
    if prefix:
        sanitized = f"{prefix}-{sanitized}"
    return sanitized[:100]


def format_duration(seconds: float) -> str:
    """Formats seconds into human-readable string like '1d 4h 20m' or '25m'."""
    if seconds < 0:
        return "N/A"
    total_seconds = int(seconds)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def render_progress_bar(pct: float, length: int = 20) -> str:
    """Renders a clean monospace progress bar."""
    pct = max(0.0, min(100.0, pct))
    filled = int(round(length * pct / 100.0))
    bar = "=" * filled + "-" * (length - filled)
    return f"`[{bar}] {pct:5.1f}%`"
