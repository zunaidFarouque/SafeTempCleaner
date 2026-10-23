import os
import pytest
from src.config.models import PathRule
from src.config.config_manager import ConfigManager
from src.core.engine import CleanerEngine


def test_gui_components_smoke(tmp_path):
    # Only test non-display logic or mocked CTk if display is headless
    cfg = ConfigManager(filepath=str(tmp_path / "config.json"))
    cfg.load()
    engine = CleanerEngine(config_manager=cfg)

    rule = cfg.get_rules()[0]
    assert rule.path != ""
    assert rule.min_age_hours == 2.0
