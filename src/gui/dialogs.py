import os
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from typing import Optional, Callable, List
from src.config.models import PathRule


class PathEditDialog(ctk.CTkToplevel):
    """
    Focused dialog for adding or editing a monitored path rule.
    Clean, uncluttered, intuitive.
    """

    def __init__(
        self,
        parent: ctk.CTk,
        rule: Optional[PathRule] = None,
        on_save: Optional[Callable[[PathRule], None]] = None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.rule = rule
        self.on_save = on_save

        is_new = rule is None
        self.title("Add Monitored Path" if is_new else "Edit Path Settings")
        self.geometry("540x440")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        self._build_ui(is_new)
        self._center_window()

    def _center_window(self) -> None:
        try:
            self.update_idletasks()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_x()
            py = self.parent.winfo_y()
            w, h = 540, 440
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self, is_new: bool) -> None:
        pad_x = 24
        pad_y = 12

        # Header
        header_text = "➕ Add Folder to Watch" if is_new else "⚙️ Path Cleanup Settings"
        lbl_header = ctk.CTkLabel(
            self,
            text=header_text,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        lbl_header.pack(anchor="w", padx=pad_x, pady=(18, 12))

        # 1. Folder Path
        lbl_path = ctk.CTkLabel(self, text="Folder Path:", font=ctk.CTkFont(weight="bold"))
        lbl_path.pack(anchor="w", padx=pad_x, pady=(4, 2))

        path_row = ctk.CTkFrame(self, fg_color="transparent")
        path_row.pack(fill="x", padx=pad_x, pady=(0, pad_y))

        self.entry_path = ctk.CTkEntry(
            path_row,
            placeholder_text=r"C:\Path\To\Folder",
            height=34,
        )
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 8))
        if self.rule:
            self.entry_path.insert(0, self.rule.path)

        btn_browse = ctk.CTkButton(
            path_row,
            text="Browse...",
            width=90,
            height=34,
            command=self._browse_folder,
        )
        btn_browse.pack(side="right")

        # 2. Age Threshold & Interval in a 2-column grid
        settings_grid = ctk.CTkFrame(self, fg_color="transparent")
        settings_grid.pack(fill="x", padx=pad_x, pady=(0, pad_y))
        settings_grid.grid_columnconfigure((0, 1), weight=1)

        # Left Column: Min Age
        col_age = ctk.CTkFrame(settings_grid, fg_color="transparent")
        col_age.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        lbl_age = ctk.CTkLabel(
            col_age,
            text="Delete Files Older Than:",
            font=ctk.CTkFont(weight="bold"),
        )
        lbl_age.pack(anchor="w", pady=(0, 2))

        age_row = ctk.CTkFrame(col_age, fg_color="transparent")
        age_row.pack(fill="x")

        initial_age = self.rule.min_age_hours if self.rule else 2.0
        self.entry_age = ctk.CTkEntry(age_row, width=80, height=34)
        self.entry_age.pack(side="left", padx=(0, 6))
        self.entry_age.insert(0, str(initial_age))

        self.age_unit = ctk.CTkOptionMenu(
            age_row,
            values=["Hours", "Minutes"],
            width=100,
            height=34,
        )
        self.age_unit.pack(side="left")
        self.age_unit.set("Hours")

        # Right Column: Check Interval
        col_interval = ctk.CTkFrame(settings_grid, fg_color="transparent")
        col_interval.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        lbl_interval = ctk.CTkLabel(
            col_interval,
            text="Check Every:",
            font=ctk.CTkFont(weight="bold"),
        )
        lbl_interval.pack(anchor="w", pady=(0, 2))

        interval_row = ctk.CTkFrame(col_interval, fg_color="transparent")
        interval_row.pack(fill="x")

        initial_interval = self.rule.interval_minutes if self.rule else 30.0
        self.entry_interval = ctk.CTkEntry(interval_row, width=80, height=34)
        self.entry_interval.pack(side="left", padx=(0, 6))
        self.entry_interval.insert(0, str(initial_interval))

        self.interval_unit = ctk.CTkOptionMenu(
            interval_row,
            values=["Minutes", "Hours"],
            width=100,
            height=34,
        )
        self.interval_unit.pack(side="left")
        self.interval_unit.set("Minutes")

        # 3. File Filter Patterns
        lbl_patterns = ctk.CTkLabel(
            self,
            text="File Patterns (* for all, or *.tmp, *.log):",
            font=ctk.CTkFont(weight="bold"),
        )
        lbl_patterns.pack(anchor="w", padx=pad_x, pady=(4, 2))

        self.entry_patterns = ctk.CTkEntry(
            self,
            placeholder_text="* (or *.tmp, *.log)",
            height=34,
        )
        self.entry_patterns.pack(fill="x", padx=pad_x, pady=(0, pad_y))
        initial_patterns = ", ".join(self.rule.file_patterns) if self.rule else "*"
        self.entry_patterns.insert(0, initial_patterns)

        # 4. Toggles (Prune Empty Subfolders & Enabled)
        toggle_row = ctk.CTkFrame(self, fg_color="transparent")
        toggle_row.pack(fill="x", padx=pad_x, pady=(4, pad_y))

        initial_prune = self.rule.prune_empty_dirs if self.rule else True
        self.switch_prune = ctk.CTkSwitch(
            toggle_row,
            text="Remove empty subfolders",
        )
        self.switch_prune.pack(side="left", padx=(0, 20))
        if initial_prune:
            self.switch_prune.select()

        initial_enabled = self.rule.enabled if self.rule else True
        self.switch_enabled = ctk.CTkSwitch(
            toggle_row,
            text="Active / Monitored",
        )
        self.switch_enabled.pack(side="left")
        if initial_enabled:
            self.switch_enabled.select()

        # Separator / Bottom Actions
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom", padx=pad_x, pady=(0, 18))

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color="gray40",
            hover_color="gray30",
            width=110,
            height=36,
            command=self.destroy,
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_save = ctk.CTkButton(
            btn_row,
            text="Save Settings",
            width=130,
            height=36,
            command=self._save_clicked,
        )
        btn_save.pack(side="right")

    def _browse_folder(self) -> None:
        initial = self.entry_path.get().strip() or os.path.expanduser("~")
        chosen = filedialog.askdirectory(parent=self, initialdir=initial, title="Select Directory to Monitor")
        if chosen:
            self.entry_path.delete(0, tk.END)
            self.entry_path.insert(0, os.path.normpath(chosen))

    def _save_clicked(self) -> None:
        path_val = self.entry_path.get().strip()
        if not path_val:
            messagebox.showwarning("Missing Folder", "Please specify a folder path to monitor.", parent=self)
            return

        # Parse age
        try:
            age_raw = float(self.entry_age.get().strip())
            if age_raw <= 0:
                raise ValueError()
            if self.age_unit.get() == "Minutes":
                min_age_hours = age_raw / 60.0
            else:
                min_age_hours = age_raw
        except ValueError:
            messagebox.showwarning("Invalid Age", "Please enter a positive number for the file age threshold.", parent=self)
            return

        # Parse interval
        try:
            int_raw = float(self.entry_interval.get().strip())
            if int_raw <= 0:
                raise ValueError()
            if self.interval_unit.get() == "Hours":
                interval_minutes = int_raw * 60.0
            else:
                interval_minutes = int_raw
        except ValueError:
            messagebox.showwarning("Invalid Interval", "Please enter a positive number for the check interval.", parent=self)
            return

        # Parse patterns
        patterns_raw = self.entry_patterns.get().strip()
        if not patterns_raw or patterns_raw == "*":
            file_patterns = ["*"]
        else:
            file_patterns = [p.strip() for p in patterns_raw.split(",") if p.strip()]
            if not file_patterns:
                file_patterns = ["*"]

        prune_dirs = bool(self.switch_prune.get())
        enabled = bool(self.switch_enabled.get())

        if self.rule:
            rule_obj = self.rule
            rule_obj.path = path_val
            rule_obj.min_age_hours = round(min_age_hours, 3)
            rule_obj.interval_minutes = round(interval_minutes, 2)
            rule_obj.file_patterns = file_patterns
            rule_obj.prune_empty_dirs = prune_dirs
            rule_obj.enabled = enabled
        else:
            rule_obj = PathRule(
                path=path_val,
                enabled=enabled,
                min_age_hours=round(min_age_hours, 3),
                interval_minutes=round(interval_minutes, 2),
                file_patterns=file_patterns,
                prune_empty_dirs=prune_dirs,
            )

        if self.on_save:
            self.on_save(rule_obj)

        self.destroy()


class AboutDialog(ctk.CTkToplevel):
    """Clean Credits and About dialog."""

    def __init__(self, parent: ctk.CTk, version: str = "1.0.0"):
        super().__init__(parent)
        self.parent = parent
        self.version = version

        self.title("About SafeTempCleaner")
        self.geometry("460x360")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._center_window()

    def _center_window(self) -> None:
        try:
            self.update_idletasks()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_x()
            py = self.parent.winfo_y()
            w, h = 460, 360
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self) -> None:
        pad_x = 24

        lbl_logo = ctk.CTkLabel(
            self,
            text="🧹 SafeTempCleaner",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        lbl_logo.pack(padx=pad_x, pady=(24, 4))

        lbl_ver = ctk.CTkLabel(
            self,
            text=f"Version v{self.version} • Standalone Windows Utility",
            text_color="gray60",
            font=ctk.CTkFont(size=12),
        )
        lbl_ver.pack(padx=pad_x, pady=(0, 16))

        lbl_desc = ctk.CTkLabel(
            self,
            text=(
                "A lightweight, non-intrusive background file cleaner engineered\n"
                "for ArcGIS batch workloads, rendering pipelines, and developer labs.\n\n"
                "Safely removes files older than your specified threshold without\n"
                "interrupting active or locked processes."
            ),
            justify="center",
            font=ctk.CTkFont(size=13),
        )
        lbl_desc.pack(padx=pad_x, pady=(0, 16))

        frame_credits = ctk.CTkFrame(self, fg_color="gray18", corner_radius=8)
        frame_credits.pack(fill="x", padx=pad_x, pady=(0, 16))

        lbl_author = ctk.CTkLabel(
            frame_credits,
            text="Created & Maintained by Md Zunaid Farouque",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_author.pack(pady=(10, 2))

        btn_github = ctk.CTkButton(
            frame_credits,
            text="🔗 View on GitHub (zunaidFarouque)",
            fg_color="transparent",
            text_color=("#3B8ED0", "#1F6AA5"),
            hover_color="gray25",
            command=lambda: webbrowser.open("https://github.com/zunaidFarouque/SafeTempCleaner"),
        )
        btn_github.pack(pady=(0, 8))

        btn_close = ctk.CTkButton(
            self,
            text="Close",
            width=100,
            command=self.destroy,
        )
        btn_close.pack(side="bottom", pady=(0, 18))
