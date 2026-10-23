import sys
import os

try:
    import win32event
    import win32api
    import win32gui
    import win32con
    import winerror
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

MUTEX_NAME = "Global\\SafeTempCleaner_SingleInstance_Mutex_v1"
MAIN_WINDOW_TITLE = "SafeTempCleaner"


class SingleInstanceChecker:
    """
    Ensures only a single instance of SafeTempCleaner runs at a time.
    If an existing instance is already running (e.g. minimized in the tray),
    this activator finds it, restores its window to foreground, and signals
    the new instance to exit.
    """

    def __init__(self, mutex_name: str = MUTEX_NAME):
        self.mutex_name = mutex_name
        self.mutex = None
        self.is_single = True

    def check_and_activate(self) -> bool:
        """
        Returns True if this is the primary instance.
        Returns False if another instance already exists (and was activated).
        """
        if not HAS_WIN32:
            return True

        try:
            self.mutex = win32event.CreateMutex(None, False, self.mutex_name)
            last_error = win32api.GetLastError()
            if last_error == winerror.ERROR_ALREADY_EXISTS:
                self.is_single = False
                self._activate_existing_instance()
                return False
            return True
        except Exception:
            return True

    def _activate_existing_instance(self) -> None:
        """Finds the existing application window and restores it to the foreground."""
        def enum_windows_callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd) or win32gui.GetWindowText(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if MAIN_WINDOW_TITLE.lower() in title.lower():
                    try:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            pass

    def release(self) -> None:
        """Releases the Win32 mutex on application exit."""
        if HAS_WIN32 and self.mutex:
            try:
                win32api.CloseHandle(self.mutex)
            except Exception:
                pass
            self.mutex = None
