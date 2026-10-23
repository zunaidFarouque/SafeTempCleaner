import os
import sys
import logging
from pathlib import Path

# Add project root to sys.path
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import customtkinter as ctk
from src.single_instance import SingleInstanceChecker
from src.config.config_manager import ConfigManager
from src.core.engine import CleanerEngine
from src.gui.app import SafeTempCleanerApp


def setup_logging():
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    setup_logging()
    logger = logging.getLogger("SafeTempCleaner")
    logger.info("Initializing SafeTempCleaner...")

    # 1. Single Instance Check
    checker = SingleInstanceChecker()
    if not checker.check_and_activate():
        logger.info("Another instance of SafeTempCleaner is already running. Focus brought to existing window. Exiting.")
        sys.exit(0)

    try:
        # 2. Load Configuration
        config_mgr = ConfigManager()
        config_mgr.load()

        # 3. Initialize Scheduler Engine
        engine = CleanerEngine(config_manager=config_mgr)

        # 4. Bootstrap Desktop GUI
        root = ctk.CTk()
        app = SafeTempCleanerApp(root=root, engine=engine, config_manager=config_mgr)

        # Handle start minimized if requested
        if config_mgr.settings.start_minimized:
            root.withdraw()

        # 5. Run GUI Loop
        root.mainloop()
    finally:
        checker.release()
        logger.info("SafeTempCleaner shutdown cleanly.")


if __name__ == "__main__":
    main()
