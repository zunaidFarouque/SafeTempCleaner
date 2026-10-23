import time
import pytest
from src.core.formatting import format_bytes, format_time_ago, format_duration


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024 * 1024 * 2.5) == "2.50 MB"
    assert format_bytes(1024 * 1024 * 1024 * 4.75) == "4.75 GB"
    assert format_bytes(1024 * 1024 * 1024 * 1024 * 1.5) == "1.50 TB"


def test_format_time_ago():
    assert format_time_ago(None) == "Never"
    assert format_time_ago(0) == "Never"
    
    now = 100000.0
    # 30 seconds ago
    assert "30s ago" in format_time_ago(now - 30, current_time=now)
    # 5 minutes 20s ago
    assert "5m 20s ago" in format_time_ago(now - 320, current_time=now)
    # 2 hours 10m ago
    assert "2h 10m ago" in format_time_ago(now - 7800, current_time=now)
    # 1 day 3 hours ago
    assert "1d 3h ago" in format_time_ago(now - 97200, current_time=now)


def test_format_duration():
    assert format_duration(0) == "0s"
    assert format_duration(45) == "45s"
    assert format_duration(120) == "2m"
    assert format_duration(3600) == "1h"
    assert format_duration(3660) == "1h 1m"
    assert format_duration(90000) == "1d 1h"
