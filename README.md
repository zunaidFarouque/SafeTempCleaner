# SafeTempCleaner

> **Created and developed by [Md Zunaid Farouque](https://github.com/zunaidFarouque)**

**SafeTempCleaner** is a lightweight, non-intrusive Windows background watchdog designed to safely purge old temporary files generated during long-running batch workloads (such as ArcGIS Lidar Analyst, 3D rendering pipelines, and computational batches) without disturbing active or locked processes.

---

## Why SafeTempCleaner?

Long computational workflows often flood local scratch drives with tens of gigabytes of intermediate files. Standard cleaners or scheduled scripts often:
1. Crash or halt execution when encountering open/locked files.
2. Prematurely wipe out active files that a background process is currently generating.
3. Require manual intervention, causing scratch drives to fill up and crash overnight runs.

**SafeTempCleaner solves this cleanly:**
- **Zero-Disruption File Safety**: If a file is currently open or locked by an active process, SafeTempCleaner gracefully skips it without crashing or interrupting your batch.
- **Activity Detection**: Only deletes files whose last modification and creation time are older than your configured threshold (default: 2 hours).
- **Bottom-Up Directory Pruning**: Removes empty subdirectories once their old contents are purged, while never deleting the monitored root itself.
- **Uncluttered & Low-Footprint**: Minimalist native dashboard that minimizes to the Windows system tray and runs with virtually 0% CPU and negligible memory.

---

## Key Features

* **Multi-Path Monitoring**: Add multiple target directories (e.g., Windows `%LOCALAPPDATA%\Temp`, ArcGIS scratch folders, custom SSD scratch disks).
* **Independent Path Rules**:
  * Individual On/Off toggles per directory.
  * Custom age threshold (e.g., files older than 2 hours or 30 minutes).
  * Custom check frequency (e.g., scan every 30 minutes).
  * File pattern filtering (e.g., `*` for everything, or `*.tmp, *.log, *.las`).
  * Automatic pruning of empty subdirectories.
* **Uncluttered Cogwheel Settings**: Concise card view on the main dashboard; click the ⚙️ cogwheel on any path to open a dedicated settings panel.
* **Instant "Run Now" Triggers**: Trigger cleanup on demand across all active paths or a single folder with one click.
* **Live Storage & Savings Metrics**: View real-time statistics on disk space cleared in the last run, total space freed during the session, and live file counts.
* **Native Windows System Tray**: Runs quietly in the notification area. Double-click to restore, or right-click for quick actions (`⚡ Run Cleanup Now`, `Pause Guard`, `Exit`).
* **Single-Instance Mutex**: Launching a second instance automatically brings the existing background window to the foreground instead of creating duplicates.

---

## Installation & Setup

### Option 1: Install via Scoop (Recommended)

If you use [Scoop](https://scoop.sh):

```powershell
# Add the bucket
scoop bucket add zunaid https://github.com/zunaidFarouque/Zunaid-Scoop-Bucket

# Install SafeTempCleaner
scoop install safetempcleaner
```

Or install directly from the manifest URL:
```powershell
scoop install https://raw.githubusercontent.com/zunaidFarouque/SafeTempCleaner/main/safetempcleaner.json
```

---

### Option 2: Standalone Portable Binary (Zero Install)

1. Download **`SafeTempCleaner-v1.0.0-windows-x64.zip`** from [Releases](https://github.com/zunaidFarouque/SafeTempCleaner/releases).
2. Extract anywhere on your PC (e.g. `C:\Tools\SafeTempCleaner`).
3. Launch **`SafeTempCleaner.exe`**.

---

### Option 3: Run from Source (Developers)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/zunaidFarouque/SafeTempCleaner.git
   cd SafeTempCleaner
   ```

2. **Set Up Virtual Environment & Dependencies**:
   ```powershell
   .\setup-env.bat
   ```

3. **Run Application**:
   ```powershell
   .\run.bat
   ```

4. **Run Tests**:
   ```powershell
   .\.venv\Scripts\pytest
   ```

---

## Building Portable Distribution

To build the standalone, portable distribution:

```powershell
.\build-portable.bat
```

The compiled binary and its assets will be output to `dist\SafeTempCleaner\`.

---

## License

This project is licensed under the [MIT License](LICENSE).
