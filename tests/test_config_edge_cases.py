import os
import json
from src.config.config_manager import ConfigManager
from src.config.models import PathRule


def test_config_manager_handles_directory_path(tmp_path):
    # Simulate Scoop creating config.json as a directory junction
    scoop_dir = tmp_path / "config.json"
    scoop_dir.mkdir()

    mgr = ConfigManager(filepath=str(scoop_dir))
    # Should not raise PermissionError!
    mgr.load()

    assert len(mgr.get_rules()) >= 1
    # Check that file was created inside the directory
    nested_file = scoop_dir / "config.json"
    assert nested_file.exists()
    assert nested_file.is_file()

    # Save should also work seamlessly
    mgr.save()
    assert nested_file.exists()


def test_config_manager_self_heals_corrupted_json(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text("{ THIS IS CORRUPTED JSON !!! }", encoding="utf-8")

    mgr = ConfigManager(filepath=str(cfg_file))
    mgr.load()

    # Must self-heal and return default configuration
    rules = mgr.get_rules()
    assert len(rules) == 1
    assert "temp" in rules[0].path.lower()


def test_config_manager_partial_or_missing_fields(tmp_path):
    cfg_file = tmp_path / "config.json"
    data = {
        "rules": [
            {
                "id": "partial-1",
                "path": "D:/Scratch",
            }
        ]
    }
    cfg_file.write_text(json.dumps(data), encoding="utf-8")

    mgr = ConfigManager(filepath=str(cfg_file))
    mgr.load()

    rule = mgr.get_rule("partial-1")
    assert rule is not None
    assert rule.path == "D:/Scratch"
    assert rule.min_age_hours == 2.0  # dataclass default applied
    assert rule.enabled is True
    assert rule.file_patterns == ["*"]


def test_config_manager_empty_rules_list_recovers_default(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"rules": []}), encoding="utf-8")

    mgr = ConfigManager(filepath=str(cfg_file))
    mgr.load()

    assert len(mgr.get_rules()) == 1
