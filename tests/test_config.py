import os
import json
from pathlib import Path
from src.config.models import PathRule, AppSettings
from src.config.config_manager import ConfigManager


def test_path_rule_serialization():
    rule = PathRule(
        id="test-1",
        path="C:/Temp",
        enabled=True,
        min_age_hours=2.5,
        interval_minutes=45.0,
        file_patterns=["*"],
        prune_empty_dirs=True,
    )
    d = rule.to_dict()
    assert d["id"] == "test-1"
    assert d["min_age_hours"] == 2.5
    assert d["interval_minutes"] == 45.0
    assert d["file_patterns"] == ["*"]

    restored = PathRule.from_dict(d)
    assert restored.id == rule.id
    assert restored.path == rule.path
    assert restored.min_age_hours == rule.min_age_hours
    assert restored.interval_minutes == rule.interval_minutes
    assert restored.file_patterns == ["*"]


def test_config_manager_default_preset(tmp_path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(filepath=str(cfg_file))
    mgr.load()

    # Must contain default Windows temp rule
    rules = mgr.get_rules()
    assert len(rules) >= 1
    default_rule = rules[0]
    assert "temp" in default_rule.path.lower()
    assert default_rule.min_age_hours == 2.0
    assert default_rule.interval_minutes == 30.0
    assert default_rule.file_patterns == ["*"]
    assert default_rule.enabled is True

    # Check file was saved
    assert cfg_file.exists()


def test_config_manager_crud_rules(tmp_path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(filepath=str(cfg_file))
    mgr.load()

    new_rule = PathRule(
        id="custom-1",
        path="D:/ArcGIS/Scratch",
        enabled=True,
        min_age_hours=1.0,
        interval_minutes=15.0,
    )
    mgr.add_rule(new_rule)
    assert len(mgr.get_rules()) == 2
    assert mgr.get_rule("custom-1") is not None

    # Update rule
    mgr.update_rule("custom-1", min_age_hours=3.0, enabled=False)
    updated = mgr.get_rule("custom-1")
    assert updated.min_age_hours == 3.0
    assert updated.enabled is False

    # Delete rule
    mgr.delete_rule("custom-1")
    assert mgr.get_rule("custom-1") is None
    assert len(mgr.get_rules()) == 1
