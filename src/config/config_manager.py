import os
import sys
import json
import threading
from typing import List, Optional, Dict, Any
from pathlib import Path
from src.config.models import PathRule, AppSettings


def get_app_directory() -> str:
    """Returns the application base directory (portable-aware for PyInstaller)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # Return repo root in development mode
    return str(Path(__file__).resolve().parent.parent.parent)


DEFAULT_CONFIG_PATH = os.path.join(get_app_directory(), "config.json")


def get_default_temp_dir() -> str:
    """Retrieves standard Windows user temp directory or fallback."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        temp_dir = os.path.join(local_app_data, "Temp")
        if os.path.exists(temp_dir):
            return temp_dir
    return os.environ.get("TEMP", os.environ.get("TMP", "C:\\Windows\\Temp"))


class ConfigManager:
    """Thread-safe manager for loading, persisting, and mutating configuration."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or DEFAULT_CONFIG_PATH
        self._lock = threading.Lock()
        self.settings = AppSettings()
        self.rules: List[PathRule] = []

    def load(self) -> None:
        """Loads configuration from JSON file. Initializes with defaults if missing."""
        with self._lock:
            if not os.path.exists(self.filepath):
                self._init_defaults()
                self._save_unlocked()
                return

            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "settings" in data and isinstance(data["settings"], dict):
                    self.settings = AppSettings.from_dict(data["settings"])
                else:
                    self.settings = AppSettings()

                self.rules = []
                if "rules" in data and isinstance(data["rules"], list):
                    for r_data in data["rules"]:
                        if isinstance(r_data, dict):
                            self.rules.append(PathRule.from_dict(r_data))

                if not self.rules:
                    self._init_defaults()
                    self._save_unlocked()
            except Exception:
                self._init_defaults()
                self._save_unlocked()

    def _init_defaults(self) -> None:
        """Sets up default preset with Windows Temp."""
        self.settings = AppSettings()
        default_rule = PathRule(
            id="default-win-temp",
            path=get_default_temp_dir(),
            enabled=True,
            min_age_hours=2.0,
            interval_minutes=30.0,
            file_patterns=["*"],
            prune_empty_dirs=True,
        )
        self.rules = [default_rule]

    def save(self) -> None:
        """Saves current configuration to disk."""
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        data = {
            "version": "1.0.0",
            "settings": self.settings.to_dict(),
            "rules": [r.to_dict() for r in self.rules],
        }
        os.makedirs(os.path.dirname(os.path.abspath(self.filepath)), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def get_rules(self) -> List[PathRule]:
        with self._lock:
            return list(self.rules)

    def get_rule(self, rule_id: str) -> Optional[PathRule]:
        with self._lock:
            for r in self.rules:
                if r.id == rule_id:
                    return r
            return None

    def add_rule(self, rule: PathRule) -> None:
        with self._lock:
            self.rules.append(rule)
            self._save_unlocked()

    def update_rule(self, rule_id: str, **kwargs) -> Optional[PathRule]:
        with self._lock:
            for r in self.rules:
                if r.id == rule_id:
                    for k, v in kwargs.items():
                        if hasattr(r, k):
                            setattr(r, k, v)
                    self._save_unlocked()
                    return r
            return None

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            initial_count = len(self.rules)
            self.rules = [r for r in self.rules if r.id != rule_id]
            if len(self.rules) != initial_count:
                self._save_unlocked()
                return True
            return False
