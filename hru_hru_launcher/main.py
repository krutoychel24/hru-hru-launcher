import sys
import traceback
import logging
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from hru_hru_launcher.ui.main_window import MinecraftLauncher


def _setup_logging():
    """Configure logging: console + rotating file in Documents/Hru Hru Studio/Hru Hru Launcher/logs/"""
    from hru_hru_launcher.utils.paths import get_launcher_data_dir
    try:
        logs_dir = Path(get_launcher_data_dir()) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "launcher.log"

        # Keep last 3 log files by rotating manually
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler]
        )
        logging.info(f"Log file: {log_file}")
    except Exception as e:
        # Fallback to console only
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logging.warning(f"Could not set up file logging: {e}")


def global_exception_hook(exctype, value, tb):
    logging.critical("--- UNHANDLED EXCEPTION (CRASH) ---")
    logging.critical("".join(traceback.format_exception(exctype, value, tb)))
    logging.critical("------------------------------------")
    sys.__excepthook__(exctype, value, tb)


def main():
    _setup_logging()
    sys.excepthook = global_exception_hook

    logging.info("=" * 50)
    logging.info("  Hru Hru Launcher starting up")
    logging.info(f"  Python {sys.version.split()[0]}")
    logging.info("=" * 50)

    app = QApplication(sys.argv)
    app.setApplicationName("Hru Hru Launcher")
    app.setOrganizationName("Hru Hru Studio")

    try:
        launcher = MinecraftLauncher()
        launcher.show()
        exit_code = app.exec()
        logging.info(f"Application exited with code {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logging.critical(f"Critical error during initialization: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
