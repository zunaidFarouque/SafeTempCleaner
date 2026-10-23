import time
from unittest.mock import patch
from src.config.models import PathRule
from src.config.config_manager import ConfigManager
from src.core.engine import CleanerEngine


def test_engine_skips_disabled_rules(tmp_path):
    cfg = ConfigManager(filepath=str(tmp_path / "config.json"))
    rule_disabled = PathRule(
        id="r-disabled",
        path=str(tmp_path / "disabled"),
        enabled=False,
    )
    rule_enabled = PathRule(
        id="r-enabled",
        path=str(tmp_path / "enabled"),
        enabled=True,
    )
    cfg.rules = [rule_disabled, rule_enabled]
    engine = CleanerEngine(config_manager=cfg)

    with patch("src.core.engine.clean_path") as mock_clean:
        from src.core.cleaner import CleanupResult
        mock_clean.return_value = CleanupResult(rule_id="r-enabled", path="enabled")

        res = engine.run_all_now()
        assert len(res) == 1
        assert res[0].rule_id == "r-enabled"
        mock_clean.assert_called_once_with(rule_enabled)


def test_engine_updates_stats_accurately(tmp_path):
    f = tmp_path / "data.tmp"
    f.write_bytes(b"1234567890")  # 10 bytes

    cfg = ConfigManager(filepath=str(tmp_path / "config.json"))
    rule = PathRule(
        id="rule-stats",
        path=str(tmp_path),
        enabled=True,
        min_age_hours=0.0,
    )
    cfg.rules = [rule]
    engine = CleanerEngine(config_manager=cfg)

    engine.run_rule_now("rule-stats")

    # Check cumulative stats
    assert engine.total_bytes_cleared == 10
    assert engine.total_files_deleted == 1
    assert engine.last_run_result is not None
    assert engine.last_run_result.bytes_cleared == 10

    # Rule in config manager should also be updated with persistence
    persisted_rule = cfg.get_rule("rule-stats")
    assert persisted_rule.last_bytes_cleared == 10
    assert persisted_rule.last_files_deleted == 1
    assert persisted_rule.last_run_time is not None
