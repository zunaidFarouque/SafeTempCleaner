import time
from unittest.mock import MagicMock
from src.config.models import PathRule
from src.config.config_manager import ConfigManager
from src.core.engine import CleanerEngine


def test_cleaner_engine_manual_run(tmp_path):
    test_file = tmp_path / "old.tmp"
    test_file.write_bytes(b"HELLO" * 10)

    cfg = ConfigManager(filepath=str(tmp_path / "config.json"))
    rule = PathRule(
        id="test-rule",
        path=str(tmp_path),
        enabled=True,
        min_age_hours=0.0,  # delete immediately for test
        interval_minutes=30.0,
    )
    cfg.rules = [rule]

    engine = CleanerEngine(config_manager=cfg)

    # Callback check
    callback = MagicMock()
    engine.on_cleanup_completed = callback

    # Trigger manual run
    results = engine.run_all_now()
    assert len(results) == 1
    assert results[0].files_deleted == 1
    assert results[0].bytes_cleared == 50
    assert not test_file.exists()
    assert engine.total_bytes_cleared == 50
    assert engine.total_files_deleted == 1

    callback.assert_called_once()


def test_cleaner_engine_start_stop(tmp_path):
    cfg = ConfigManager(filepath=str(tmp_path / "config.json"))
    cfg.rules = []
    engine = CleanerEngine(config_manager=cfg)

    assert not engine.is_running
    engine.start()
    assert engine.is_running

    engine.stop()
    assert not engine.is_running
