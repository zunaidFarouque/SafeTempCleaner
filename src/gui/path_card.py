import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from pathlib import Path
from typing import Callable, Optional
from src.config.models import PathRule
from src.core.formatting import format_bytes, format_time_ago, format_duration
from src.core.storage import inspect_directory_stats


class PathCard(ctk.CTkFrame):
    """
    Uncluttered, concise card widget representing a single monitored path.
    Shows the path, status chips, live folder size, and quick action buttons.
    """

    def __init__(
        self,
        parent,
        rule: PathRule,
        on_toggle: Callable[[str, bool], None],
        on_edit: Callable[[PathRule], None],
        on_run_now: Callable[[str], None],
        on_delete: Callable[[str], None],
    ):
        super().__init__(parent, fg_color=("gray90", "gray17"), corner_radius=8)
        self.rule = rule
        self.on_toggle = on_toggle
        self.on_edit = on_edit
        self.on_run_now = on_run_now
        self.on_delete = on_delete

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)

        # 1. Left: Active Toggle Switch
        self.switch_var = tk.BooleanVar(value=self.rule.enabled)
        self.switch = ctk.CTkSwitch(
            self,
            text="",
            variable=self.switch_var,
            width=46,
            command=self._on_switch_toggled,
        )
        self.switch.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=12, sticky="w")

        # 2. Middle: Path & Info Details
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="w", padx=4, pady=(10, 2))

        # Truncate long paths visually for clean appearance
        display_path = self.rule.path
        if len(display_path) > 55:
            display_path = display_path[:26] + "..." + display_path[-26:]

        self.lbl_path = ctk.CTkLabel(
            info_frame,
            text=display_path,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self.lbl_path.pack(anchor="w")

        # Format chips summary
        age_str = f"> {self.rule.min_age_hours}h old"
        interval_str = f"every {int(self.rule.interval_minutes)}m" if self.rule.interval_minutes >= 1 else f"every {self.rule.interval_minutes}m"
        pattern_str = ", ".join(self.rule.file_patterns)

        # Inspect folder contents for live file count & size
        folder_stats = inspect_directory_stats(Path(self.rule.path))
        files_str = f"{folder_stats['file_count']} files ({format_bytes(folder_stats['total_bytes'])})"

        chips_text = f"{age_str}  •  {interval_str}  •  [{pattern_str}]  •  {files_str}"
        self.lbl_chips = ctk.CTkLabel(
            self,
            text=chips_text,
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            anchor="w",
        )
        self.lbl_chips.grid(row=1, column=1, sticky="w", padx=4, pady=(0, 10))

        # 3. Right: Action Buttons (Run Now, Cogwheel Edit, Delete)
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=0, column=2, rowspan=2, padx=(10, 14), pady=10, sticky="e")

        btn_run = ctk.CTkButton(
            actions_frame,
            text="⚡ Run",
            width=64,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#3B8ED0", "#1F6AA5"),
            hover_color=("#36719F", "#144870"),
            command=lambda: self.on_run_now(self.rule.id),
        )
        btn_run.pack(side="left", padx=4)

        btn_edit = ctk.CTkButton(
            actions_frame,
            text="⚙️",
            width=36,
            height=30,
            fg_color="gray30",
            hover_color="gray40",
            command=lambda: self.on_edit(self.rule),
        )
        btn_edit.pack(side="left", padx=4)

        btn_del = ctk.CTkButton(
            actions_frame,
            text="🗑️",
            width=36,
            height=30,
            fg_color="gray30",
            hover_color="#A83232",
            command=self._confirm_delete,
        )
        btn_del.pack(side="left", padx=4)

    def _on_switch_toggled(self) -> None:
        new_val = self.switch_var.get()
        self.rule.enabled = new_val
        self.on_toggle(self.rule.id, new_val)

    def _confirm_delete(self) -> None:
        if messagebox.askyesno(
            "Remove Path",
            f"Are you sure you want to stop monitoring this path?\n\n{self.rule.path}",
            parent=self.winfo_toplevel(),
        ):
            self.on_delete(self.rule.id)
