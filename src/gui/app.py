import os
import time
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from pathlib import Path
from typing import Optional

from src.config.models import PathRule
from src.config.config_manager import ConfigManager
from src.core.engine import CleanerEngine
from src.core.formatting import format_bytes, format_time_ago
from src.core.storage import get_drive_storage
from src.gui.path_card import PathCard
from src.gui.dialogs import PathEditDialog, AboutDialog
from src.gui.tray import Win32SystemTray

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SafeTempCleanerApp:
    """Main desktop application window for SafeTempCleaner."""

    def __init__(self, root: ctk.CTk, engine: CleanerEngine, config_manager: ConfigManager):
        self.root = root
        self.engine = engine
        self.config_manager = config_manager
        self.settings = config_manager.settings

        self.root.title("SafeTempCleaner - Safe Windows Temp Watchdog")
        self.root.geometry("860x640")
        self.root.minsize(760, 540)

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(getattr(sys, "_MEIPASS", ""), "assets", "icon.ico")
        if not os.path.exists(icon_path) and getattr(sys, "frozen", False):
            icon_path = os.path.join(os.path.dirname(sys.executable), "SafeTempCleaner_files", "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Wire engine callbacks
        self.engine.on_cleanup_completed = lambda res: self.root.after(0, self._on_cleanup_done, res)
        self.engine.on_stats_updated = lambda: self.root.after(0, self._refresh_stats_display)

        # Initialize System Tray
        self.tray = Win32SystemTray(
            tooltip="SafeTempCleaner • ACTIVE",
            on_show=self._show_from_tray,
            on_toggle_engine=lambda: self.root.after(0, self._toggle_engine),
            on_run_now=lambda: self.root.after(0, self._run_all_now),
            on_quit=lambda: self.root.after(0, self.quit_app),
        )
        self.tray.start()

        # Intercept window close to minimize to tray
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._build_ui()
        self._refresh_paths_list()
        self._refresh_stats_display()

        # Center window and focus
        self._center_and_focus()

        # Start background engine if enabled
        if self.settings.auto_start_engine:
            self.engine.start()
            self._update_status_indicator()

        # Periodic refresh timer for live stats and folder counts
        self._schedule_periodic_refresh()

    def _center_and_focus(self) -> None:
        try:
            self.root.update_idletasks()
            w, h = 860, 640
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after_idle(lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except Exception:
            pass

    def _build_ui(self) -> None:
        # Top Header Bar
        header = ctk.CTkFrame(self.root, height=64, corner_radius=0, fg_color=("gray85", "gray14"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        # Title & Status Badge
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=12)

        lbl_title = ctk.CTkLabel(
            title_frame,
            text="🧹 SafeTempCleaner",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        lbl_title.pack(side="left", padx=(0, 12))

        self.lbl_status_badge = ctk.CTkLabel(
            title_frame,
            text="🟢 Guard Active",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4CAF50",
            fg_color=("gray75", "gray20"),
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.lbl_status_badge.pack(side="left")

        # Top Action Buttons
        actions_frame = ctk.CTkFrame(header, fg_color="transparent")
        actions_frame.pack(side="right", padx=20, pady=12)

        self.btn_run_all = ctk.CTkButton(
            actions_frame,
            text="⚡ Run All Now",
            width=120,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._run_all_now,
        )
        self.btn_run_all.pack(side="left", padx=6)

        btn_add = ctk.CTkButton(
            actions_frame,
            text="➕ Add Folder",
            width=110,
            height=34,
            fg_color="gray30",
            hover_color="gray40",
            command=self._open_add_dialog,
        )
        btn_add.pack(side="left", padx=6)

        btn_about = ctk.CTkButton(
            actions_frame,
            text="ℹ️ About",
            width=80,
            height=34,
            fg_color="gray30",
            hover_color="gray40",
            command=lambda: AboutDialog(self.root),
        )
        btn_about.pack(side="left", padx=6)

        # Top Metrics Cards Row
        metrics_bar = ctk.CTkFrame(self.root, fg_color="transparent")
        metrics_bar.pack(fill="x", padx=20, pady=(16, 10))
        metrics_bar.grid_columnconfigure((0, 1, 2), weight=1)

        # Card 1: Last Run Cleared
        card_last = ctk.CTkFrame(metrics_bar, corner_radius=8, fg_color=("gray90", "gray17"))
        card_last.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(card_last, text="CLEARED LAST RUN", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_val_last_bytes = ctk.CTkLabel(card_last, text="0 B", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_val_last_bytes.pack(anchor="w", padx=14)
        self.lbl_sub_last = ctk.CTkLabel(card_last, text="0 files deleted", font=ctk.CTkFont(size=12), text_color="gray60")
        self.lbl_sub_last.pack(anchor="w", padx=14, pady=(0, 10))

        # Card 2: Total Session Cleared
        card_total = ctk.CTkFrame(metrics_bar, corner_radius=8, fg_color=("gray90", "gray17"))
        card_total.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(card_total, text="TOTAL CLEARED (SESSION)", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_val_total_bytes = ctk.CTkLabel(card_total, text="0 B", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_val_total_bytes.pack(anchor="w", padx=14)
        self.lbl_sub_total = ctk.CTkLabel(card_total, text="0 files purged", font=ctk.CTkFont(size=12), text_color="gray60")
        self.lbl_sub_total.pack(anchor="w", padx=14, pady=(0, 10))

        # Card 3: Storage Free Space
        card_storage = ctk.CTkFrame(metrics_bar, corner_radius=8, fg_color=("gray90", "gray17"))
        card_storage.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(card_storage, text="PRIMARY STORAGE HEALTH", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(anchor="w", padx=14, pady=(10, 2))
        self.lbl_val_storage = ctk.CTkLabel(card_storage, text="-- GB Free", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_val_storage.pack(anchor="w", padx=14)
        self.lbl_sub_storage = ctk.CTkLabel(card_storage, text="Calculating...", font=ctk.CTkFont(size=12), text_color="gray60")
        self.lbl_sub_storage.pack(anchor="w", padx=14, pady=(0, 10))

        # Middle: Monitored Folders Section Header
        sec_header = ctk.CTkFrame(self.root, fg_color="transparent")
        sec_header.pack(fill="x", padx=20, pady=(10, 6))

        self.lbl_paths_header = ctk.CTkLabel(
            sec_header,
            text="Monitored Folders",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.lbl_paths_header.pack(side="left")

        # Scrollable Paths Container
        self.paths_container = ctk.CTkScrollableFrame(
            self.root,
            fg_color="transparent",
            corner_radius=0,
        )
        self.paths_container.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Bottom Status Bar
        status_bar = ctk.CTkFrame(self.root, height=38, corner_radius=0, fg_color=("gray85", "gray14"))
        status_bar.pack(fill="x", side="bottom")

        self.lbl_footer_status = ctk.CTkLabel(
            status_bar,
            text="Ready. SafeTempCleaner is guarding your temp directories.",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self.lbl_footer_status.pack(side="left", padx=20)

        self.btn_toggle_engine = ctk.CTkButton(
            status_bar,
            text="Pause Guard",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="gray30",
            hover_color="gray40",
            command=self._toggle_engine,
        )
        self.btn_toggle_engine.pack(side="right", padx=20, pady=6)

    def _refresh_paths_list(self) -> None:
        """Destroys and recreates path cards in the container."""
        for widget in self.paths_container.winfo_children():
            widget.destroy()

        rules = self.config_manager.get_rules()
        active_count = sum(1 for r in rules if r.enabled)
        self.lbl_paths_header.configure(text=f"Monitored Folders ({active_count} active / {len(rules)} total)")

        if not rules:
            empty_frame = ctk.CTkFrame(self.paths_container, fg_color=("gray90", "gray17"), corner_radius=8)
            empty_frame.pack(fill="x", pady=20, padx=10)
            ctk.CTkLabel(
                empty_frame,
                text="No folders monitored yet.\nClick [➕ Add Folder] to add your first cleanup directory.",
                font=ctk.CTkFont(size=14),
                text_color="gray60",
            ).pack(pady=30)
            return

        for rule in rules:
            card = PathCard(
                parent=self.paths_container,
                rule=rule,
                on_toggle=self._on_rule_toggle,
                on_edit=self._open_edit_dialog,
                on_run_now=self._run_single_path_now,
                on_delete=self._on_rule_delete,
            )
            card.pack(fill="x", pady=5)

    def _refresh_stats_display(self) -> None:
        """Updates top summary metric cards and tray status."""
        last_res = self.engine.last_run_result
        if last_res:
            self.lbl_val_last_bytes.configure(text=format_bytes(last_res.bytes_cleared))
            skipped_str = f" • {last_res.files_skipped} locked" if last_res.files_skipped > 0 else ""
            self.lbl_sub_last.configure(
                text=f"{last_res.files_deleted} deleted{skipped_str} • {format_time_ago(last_res.timestamp)}"
            )

        self.lbl_val_total_bytes.configure(text=format_bytes(self.engine.total_bytes_cleared))
        self.lbl_sub_total.configure(
            text=f"{self.engine.total_files_deleted} files purged ({self.engine.total_dirs_deleted} dirs)"
        )

        # Primary storage health
        rules = self.config_manager.get_rules()
        if rules:
            primary_path = Path(rules[0].path)
            storage = get_drive_storage(primary_path)
            self.lbl_val_storage.configure(text=f"{storage['free_gb']:.1f} GB Free")
            self.lbl_sub_storage.configure(text=f"{storage['drive']} ({storage['used_pct']}% used) {storage['badge']}")

        active_count = sum(1 for r in rules if r.enabled)
        self.tray.update_status(self.engine.is_running, active_count)

    def _schedule_periodic_refresh(self) -> None:
        """Periodically refreshes folder file counts and stats every 15 seconds."""
        self._refresh_stats_display()
        self.root.after(15000, self._schedule_periodic_refresh)

    def _on_rule_toggle(self, rule_id: str, enabled: bool) -> None:
        self.config_manager.update_rule(rule_id, enabled=enabled)
        active_count = sum(1 for r in self.config_manager.get_rules() if r.enabled)
        self.lbl_paths_header.configure(text=f"Monitored Folders ({active_count} active / {len(self.config_manager.get_rules())} total)")
        self.tray.update_status(self.engine.is_running, active_count)

    def _open_add_dialog(self) -> None:
        def save_new(rule: PathRule):
            self.config_manager.add_rule(rule)
            self._refresh_paths_list()
            self._refresh_stats_display()

        PathEditDialog(parent=self.root, rule=None, on_save=save_new)

    def _open_edit_dialog(self, rule: PathRule) -> None:
        def save_existing(updated: PathRule):
            self.config_manager.update_rule(
                updated.id,
                path=updated.path,
                enabled=updated.enabled,
                min_age_hours=updated.min_age_hours,
                interval_minutes=updated.interval_minutes,
                file_patterns=updated.file_patterns,
                prune_empty_dirs=updated.prune_empty_dirs,
            )
            self._refresh_paths_list()
            self._refresh_stats_display()

        PathEditDialog(parent=self.root, rule=rule, on_save=save_existing)

    def _on_rule_delete(self, rule_id: str) -> None:
        self.config_manager.delete_rule(rule_id)
        self._refresh_paths_list()
        self._refresh_stats_display()

    def _run_single_path_now(self, rule_id: str) -> None:
        rule = self.config_manager.get_rule(rule_id)
        if not rule:
            return
        self.lbl_footer_status.configure(text=f"Cleaning {rule.path}...")
        threading.Thread(target=lambda: self.engine.run_rule_now(rule_id), daemon=True).start()

    def _run_all_now(self) -> None:
        self.btn_run_all.configure(state="disabled", text="⚡ Cleaning...")
        self.lbl_footer_status.configure(text="Running cleanup across all active folders...")

        def worker():
            try:
                self.engine.run_all_now()
            finally:
                self.root.after(0, lambda: self.btn_run_all.configure(state="normal", text="⚡ Run All Now"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_cleanup_done(self, result) -> None:
        self._refresh_paths_list()
        self._refresh_stats_display()
        self.lbl_footer_status.configure(
            text=f"Last run complete: Cleared {format_bytes(result.bytes_cleared)} across {result.files_deleted} files."
        )

    def _toggle_engine(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
        else:
            self.engine.start()
        self._update_status_indicator()

    def _update_status_indicator(self) -> None:
        running = self.engine.is_running
        if running:
            self.lbl_status_badge.configure(text="🟢 Guard Active", text_color="#4CAF50")
            self.btn_toggle_engine.configure(text="Pause Guard")
            self.lbl_footer_status.configure(text="SafeTempCleaner guard is active and watching.")
        else:
            self.lbl_status_badge.configure(text="⏸️ Guard Paused", text_color="#FFA000")
            self.btn_toggle_engine.configure(text="Resume Guard")
            self.lbl_footer_status.configure(text="Background monitoring is paused.")
        active_count = sum(1 for r in self.config_manager.get_rules() if r.enabled)
        self.tray.update_status(running, active_count)

    def _on_window_close(self) -> None:
        """Minimizes window to system tray instead of terminating."""
        self.root.withdraw()

    def _show_from_tray(self) -> None:
        """Restores window from system tray and focuses it."""
        self.root.after(0, self._restore_window)

    def _restore_window(self) -> None:
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after_idle(lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except Exception:
            pass

    def quit_app(self) -> None:
        """Fully terminates application, engine, and tray."""
        try:
            self.engine.stop()
            self.tray.stop()
            self.root.destroy()
        except Exception:
            pass
