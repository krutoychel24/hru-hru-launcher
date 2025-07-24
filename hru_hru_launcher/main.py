import sys
import traceback
import logging
from PySide6.QtWidgets import QApplication
from hru_hru_launcher.ui.main_window import MinecraftLauncher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def global_exception_hook(exctype, value, tb):
    logging.critical("--- GLOBAL EXCEPTION (CRASH) ---")
    logging.critical("".join(traceback.format_exception(exctype, value, tb)))
    logging.critical("----------------------------------")
    sys.__excepthook__(exctype, value, tb)

def main():
    sys.excepthook = global_exception_hook
    
    logging.info("Starting Hru Hru Launcher application.")
    app = QApplication(sys.argv)
    
    try:
        launcher = MinecraftLauncher()
        launcher.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Critical error during application initialization: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
