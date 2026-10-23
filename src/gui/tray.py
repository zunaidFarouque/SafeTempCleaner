import sys
import threading
from typing import Optional, Callable

try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class Win32SystemTray:
    """
    Native Windows System Tray (Notification Area) integration using win32gui.
    Runs a lightweight Win32 message pump in a daemon thread so it never blocks Tkinter.
    Provides context menu (Show Dashboard, Toggle Guard, Run All Now, Quit) and single/double-click restore.
    """

    def __init__(
        self,
        tooltip: str = "SafeTempCleaner",
        on_show: Optional[Callable[[], None]] = None,
        on_toggle_engine: Optional[Callable[[], None]] = None,
        on_run_now: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ):
        self.tooltip = tooltip
        self.on_show = on_show
        self.on_toggle_engine = on_toggle_engine
        self.on_run_now = on_run_now
        self.on_quit = on_quit

        self.engine_running: bool = False
        self.hwnd = None
        self._thread: Optional[threading.Thread] = None
        self.is_registered: bool = False
        self._is_alive: bool = False

    def start(self) -> None:
        """Starts the Win32 message loop in a background daemon thread."""
        if not HAS_WIN32:
            return
        self._is_alive = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="Win32TrayThread"
        )
        self._thread.start()

    def update_status(self, engine_running: bool, active_paths: int = 0) -> None:
        """Updates internal status and the tray tooltip."""
        self.engine_running = engine_running
        state_str = "ACTIVE" if engine_running else "PAUSED"
        self.update_tooltip(f"SafeTempCleaner • {state_str} ({active_paths} paths)")

    def update_tooltip(self, text: str) -> None:
        """Modifies the mouseover tooltip text."""
        self.tooltip = text[:127]  # Win32 NOTIFYICONDATA tooltip length limit
        if HAS_WIN32 and self.hwnd and self.is_registered:
            try:
                nid = (self.hwnd, 0, win32gui.NIF_TIP, 0, 0, self.tooltip)
                win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
            except Exception:
                pass

    def stop(self) -> None:
        """Cleans up the tray icon and terminates the message pump."""
        self._is_alive = False
        if HAS_WIN32 and self.hwnd:
            if self.is_registered:
                try:
                    nid = (self.hwnd, 0)
                    win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
                except Exception:
                    pass
                self.is_registered = False
            try:
                win32gui.PostMessage(self.hwnd, win32con.WM_DESTROY, 0, 0)
            except Exception:
                pass

    def _run(self) -> None:
        try:
            wc = win32gui.WNDCLASS()
            wc.hInstance = win32gui.GetModuleHandle(None)
            wc.lpszClassName = f"SafeTempCleanerTray_{id(self)}"
            wc.lpfnWndProc = self._wnd_proc

            class_atom = win32gui.RegisterClass(wc)
            self.hwnd = win32gui.CreateWindow(
                class_atom,
                "SafeTempCleanerTrayHelper",
                win32con.WS_OVERLAPPED | win32con.WS_SYSMENU,
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                0, 0, wc.hInstance, None
            )
            win32gui.UpdateWindow(self.hwnd)
            self._register_tray_icon()

            win32gui.PumpMessages()
        except Exception:
            pass
        finally:
            self.is_registered = False

    def _register_tray_icon(self) -> None:
        try:
            hicon = None
            # Check for custom icon
            possible_icons = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.ico"),
                os.path.join(getattr(sys, "_MEIPASS", ""), "assets", "icon.ico"),
            ]
            for p in possible_icons:
                if os.path.exists(p):
                    try:
                        hicon = win32gui.LoadImage(
                            0, p, win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
                        )
                        if hicon:
                            break
                    except Exception:
                        pass

            if not hicon:
                hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

            flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
            nid = (self.hwnd, 0, flags, win32con.WM_USER + 20, hicon, self.tooltip[:127])
            win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
            self.is_registered = True
        except Exception:
            self.is_registered = False

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_USER + 20:
            if lparam in (win32con.WM_LBUTTONDBLCLK, win32con.WM_LBUTTONUP):
                if self.on_show:
                    self.on_show()
            elif lparam == win32con.WM_RBUTTONUP:
                self._show_context_menu()
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _show_context_menu(self) -> None:
        try:
            menu = win32gui.CreatePopupMenu()
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1001, "Open SafeTempCleaner")
            guard_text = "Pause Background Guard" if self.engine_running else "Resume Background Guard"
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1002, guard_text)
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1003, "⚡ Run Cleanup Now")
            win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
            win32gui.AppendMenu(menu, win32con.MF_STRING, 1004, "Quit SafeTempCleaner")

            pos = win32gui.GetCursorPos()
            win32gui.SetForegroundWindow(self.hwnd)
            cmd = win32gui.TrackPopupMenu(
                menu,
                win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD | win32con.TPM_NONOTIFY,
                pos[0], pos[1], 0, self.hwnd, None
            )
            win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

            if cmd == 1001 and self.on_show:
                self.on_show()
            elif cmd == 1002 and self.on_toggle_engine:
                self.on_toggle_engine()
            elif cmd == 1003 and self.on_run_now:
                self.on_run_now()
            elif cmd == 1004 and self.on_quit:
                self.on_quit()
        except Exception:
            pass
