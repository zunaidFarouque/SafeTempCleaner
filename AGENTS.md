# SafeTempCleaner - Agent Guidelines & Architecture Reference

## Overview
**SafeTempCleaner** is a lightweight, non-intrusive Windows background watchdog engine designed to safely purge old temporary files generated during long-running batch workloads (e.g. ArcGIS Lidar Analyst, rendering pipelines, compiler caches) without disturbing active processes.

## Architecture

```
SafeTempCleaner/
├── src/
│   ├── core/
│   │   ├── cleaner.py          # File walk, age filter, locked-file skipping (safe unlink)
│   │   ├── engine.py           # Background multi-path scheduler daemon
│   │   ├── storage.py          # Disk usage & drive health metrics
│   │   └── formatting.py       # Byte, duration, and time-ago formatters
│   ├── config/
│   │   ├── models.py           # PathRule and AppSettings dataclasses
│   │   └── config_manager.py   # Thread-safe config.json persistence
│   ├── gui/
│   │   ├── app.py              # Main CustomTkinter dashboard
│   │   ├── path_card.py        # Concise monitored path card widget
│   │   ├── dialogs.py          # PathEditDialog (cogwheel settings) & AboutDialog
│   │   └── tray.py             # Native Win32 system tray notification icon
│   ├── single_instance.py      # Win32 Mutex to prevent duplicate tray instances
│   └── main.py                 # Application entrypoint
├── tests/                      # Pytest suite
├── scripts/
│   └── release.ps1             # Automated packaging and Scoop bucket sync
├── safetempcleaner.json         # Canonical Scoop package manifest
├── build-portable.bat          # PyInstaller standalone portable folder compiler
├── requirements.txt            # Minimal dependencies
└── config.json                 # Persisted configuration
```

## Critical Safety Rule: Releases

> [!CAUTION]
> **CRITICAL SAFETY RULE: RELEASES**
> NEVER execute `scripts/release.ps1` without the user's explicit, direct permission in the current prompt (e.g., "Please release version X.Y.Z"). Agents may build, test, and edit files, but must never autonomously trigger an official GitHub release or push release tags.
