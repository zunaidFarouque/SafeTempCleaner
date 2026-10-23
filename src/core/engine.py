import time
import threading
import logging
from typing import List, Optional, Callable, Dict
from src.config.models import PathRule
from src.config.config_manager import ConfigManager
from src.core.cleaner import clean_path, CleanupResult

logger = logging.getLogger("SafeTempCleaner.engine")


class CleanerEngine:
    """
    Background scheduler engine.
    Periodically checks monitored paths according to each rule's interval,
    dispatches cleanups, tracks global metrics, and provides manual triggers.
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Cumulative session metrics
        self.total_bytes_cleared: int = 0
        self.total_files_deleted: int = 0
        self.total_files_skipped: int = 0
        self.total_dirs_deleted: int = 0
        self.last_run_result: Optional[CleanupResult] = None
        self.last_run_time: Optional[float] = None

        # Next check timetable per rule_id: timestamp
        self._next_check_times: Dict[str, float] = {}

        # Callbacks
        self.on_cleanup_completed: Optional[Callable[[CleanupResult], None]] = None
        self.on_stats_updated: Optional[Callable[[], None]] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Starts the background monitoring thread."""
        with self._lock:
            if self.is_running:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._worker_loop, daemon=True, name="CleanerEngineWorker"
            )
            self._thread.start()
            logger.info("CleanerEngine started.")

    def stop(self) -> None:
        """Signals the background thread to stop and waits for exit."""
        with self._lock:
            self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("CleanerEngine stopped.")

    def run_rule_now(self, rule_id: str) -> Optional[CleanupResult]:
        """Manually runs cleanup on a specific rule immediately."""
        rule = self.config_manager.get_rule(rule_id)
        if not rule:
            return None
        return self._execute_and_record(rule)

    def run_all_now(self) -> List[CleanupResult]:
        """Manually runs cleanup on all enabled rules immediately."""
        rules = [r for r in self.config_manager.get_rules() if r.enabled]
        results = []
        for r in rules:
            res = self._execute_and_record(r)
            results.append(res)
        return results

    def _execute_and_record(self, rule: PathRule) -> CleanupResult:
        """Executes cleanup for a rule and updates in-memory and persisted metrics."""
        result = clean_path(rule)

        with self._lock:
            self.total_bytes_cleared += result.bytes_cleared
            self.total_files_deleted += result.files_deleted
            self.total_files_skipped += result.files_skipped
            self.total_dirs_deleted += result.dirs_deleted
            self.last_run_result = result
            self.last_run_time = result.timestamp

            # Schedule next run time based on rule's interval
            interval_sec = max(60.0, rule.interval_minutes * 60.0)
            self._next_check_times[rule.id] = time.time() + interval_sec

        # Update persisted rule stats
        self.config_manager.update_rule(
            rule.id,
            last_run_time=result.timestamp,
            last_bytes_cleared=result.bytes_cleared,
            last_files_deleted=result.files_deleted,
            last_files_skipped=result.files_skipped,
            last_files_retained=result.files_retained,
            last_dirs_deleted=result.dirs_deleted,
        )

        if self.on_cleanup_completed:
            try:
                self.on_cleanup_completed(result)
            except Exception as err:
                logger.error(f"Error in on_cleanup_completed callback: {err}")

        if self.on_stats_updated:
            try:
                self.on_stats_updated()
            except Exception as err:
                logger.error(f"Error in on_stats_updated callback: {err}")

        return result

    def _worker_loop(self) -> None:
        """Main loop: runs periodically, checking due paths."""
        logger.info("CleanerEngine background loop entered.")
        while not self._stop_event.is_set():
            now = time.time()
            rules = self.config_manager.get_rules()

            for rule in rules:
                if not rule.enabled:
                    continue

                next_time = self._next_check_times.get(rule.id, 0.0)
                if now >= next_time:
                    self._execute_and_record(rule)

            # Sleep in small slices to remain responsive to shutdown
            self._stop_event.wait(timeout=2.0)

        logger.info("CleanerEngine background loop terminated.")
