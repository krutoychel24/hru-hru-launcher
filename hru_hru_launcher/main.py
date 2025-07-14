import sys
import traceback
import logging
from datetime import datetime
from PySide6.QtWidgets import QApplication
from hru_hru_launcher.ui.main_window import MinecraftLauncher

# --- НАСТРОЙКА ЛОГИРОВАНИЯ В ФАЙЛ ---
log_filename = "hru_hru_launcher.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # Также выводим в консоль
    ]
)

def global_exception_hook(exctype, value, tb):
    """ Глобальный обработчик для записи неперехваченных ошибок. """
    logging.critical("--- ГЛОБАЛЬНОЕ ИСКЛЮЧЕНИЕ (КРАШ) ---")
    logging.critical("".join(traceback.format_exception(exctype, value, tb)))
    logging.critical("------------------------------------")
    sys.__excepthook__(exctype, value, tb)

def main():
    """ Основная функция для запуска лаунчера. """
    # Устанавливаем наш обработчик ошибок
    sys.excepthook = global_exception_hook
    
    logging.info("Запуск приложения Hru Hru Launcher.")
    app = QApplication(sys.argv)
    
    try:
        launcher = MinecraftLauncher()
        launcher.show()
        sys.exit(app.exec())
    except Exception as e:
        # Ловим любые ошибки на этапе инициализации
        logging.critical(f"Критическая ошибка при инициализации приложения: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()