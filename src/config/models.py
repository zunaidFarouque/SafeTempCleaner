from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
import uuid


@dataclass
class PathRule:
    """Represents a monitored directory path and its cleanup rules."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    path: str = ""
    enabled: bool = True
    min_age_hours: float = 2.0
    interval_minutes: float = 30.0
    file_patterns: List[str] = field(default_factory=lambda: ["*"])
    prune_empty_dirs: bool = True
    last_run_time: Optional[float] = None
    last_bytes_cleared: int = 0
    last_files_deleted: int = 0
    last_files_skipped: int = 0
    last_files_retained: int = 0
    last_dirs_deleted: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PathRule":
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class AppSettings:
    """Global application preferences."""
    minimize_to_tray: bool = True
    start_minimized: bool = False
    auto_start_engine: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
