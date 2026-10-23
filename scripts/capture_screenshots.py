import os
import sys
import time
import ctypes
from pathlib import Path
import win32gui
import win32ui
import win32con
from PIL import Image

# Ensure project root is in sys.path
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import customtkinter as ctk
from src.config.models import PathRule, AppSettings
from src.config.config_manager import ConfigManager
from src.core.engine import CleanerEngine
from src.core.cleaner import CleanupResult
from src.gui.app import SafeTempCleanerApp
from src.gui.dialogs import PathEditDialog, AboutDialog


def capture_window_to_file(hwnd: int, output_path: str):
    rect = win32gui.GetWindowRect(hwnd)
    w = max(10, rect[2] - rect[0])
    h = max(10, rect[3] - rect[1])

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    # PW_RENDERFULLCONTENT = 2
    ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer("RGB", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRX", 0, 1)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    im.save(output_path)
    print(f"Captured: {output_path} ({w}x{h})")

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)


def main():
    artifact_dir = r"C:\Users\Zunaid\.gemini\antigravity\brain\94cf84a2-8929-4178-80c4-6fab8e5137b7"
    assets_dir = os.path.join(_REPO_ROOT, "assets")
    os.makedirs(artifact_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)

    # Create dummy config with 2 realistic paths
    temp_dir = os.environ.get("TEMP", r"C:\Users\User\AppData\Local\Temp")
    r1 = PathRule(
        id="rule-win-temp",
        path=temp_dir,
        enabled=True,
        min_age_hours=2.0,
        interval_minutes=30.0,
        file_patterns=["*"],
        prune_empty_dirs=True,
        last_bytes_cleared=1420000000,
        last_files_deleted=48,
        last_files_skipped=3,
        last_run_time=time.time() - 360,
    )
    r2 = PathRule(
        id="rule-arcgis",
        path=r"D:\ArcGIS_Workloads\Lidar_Batch\Scratch",
        enabled=True,
        min_age_hours=1.5,
        interval_minutes=15.0,
        file_patterns=["*.tmp", "*.las", "*.log"],
        prune_empty_dirs=True,
        last_bytes_cleared=3850000000,
        last_files_deleted=112,
        last_files_skipped=0,
        last_run_time=time.time() - 120,
    )

    cfg = ConfigManager()
    cfg.rules = [r1, r2]
    engine = CleanerEngine(config_manager=cfg)
    engine.total_bytes_cleared = 5270000000  # 5.27 GB
    engine.total_files_deleted = 160
    engine.total_dirs_deleted = 14
    engine.last_run_result = CleanupResult(
        rule_id="rule-arcgis",
        path=r2.path,
        bytes_cleared=3850000000,
        files_deleted=112,
        files_skipped=0,
        dirs_deleted=8,
        timestamp=time.time() - 120,
    )

    # 1. Main Dashboard
    root = ctk.CTk()
    app = SafeTempCleanerApp(root=root, engine=engine, config_manager=cfg)
    root.update()
    time.sleep(0.5)
    root.update()

    dash_art = os.path.join(artifact_dir, "dashboard.png")
    dash_repo = os.path.join(assets_dir, "dashboard.png")
    capture_window_to_file(root.winfo_id(), dash_art)
    capture_window_to_file(root.winfo_id(), dash_repo)

    # 2. Path Settings Dialog (Cogwheel)
    edit_dialog = PathEditDialog(parent=root, rule=r2)
    edit_dialog.update()
    time.sleep(0.5)
    edit_dialog.update()

    cog_art = os.path.join(artifact_dir, "path_settings_dialog.png")
    cog_repo = os.path.join(assets_dir, "path_settings_dialog.png")
    capture_window_to_file(edit_dialog.winfo_id(), cog_art)
    capture_window_to_file(edit_dialog.winfo_id(), cog_repo)
    edit_dialog.destroy()

    # 3. About Dialog
    about_dialog = AboutDialog(parent=root, version="1.0.0")
    about_dialog.update()
    time.sleep(0.5)
    about_dialog.update()

    about_art = os.path.join(artifact_dir, "about_dialog.png")
    about_repo = os.path.join(assets_dir, "about_dialog.png")
    capture_window_to_file(about_dialog.winfo_id(), about_art)
    capture_window_to_file(about_dialog.winfo_id(), about_repo)
    about_dialog.destroy()

    app.quit_app()
    print("All screenshots captured successfully!")


if __name__ == "__main__":
    main()
