# core/updater.py
import requests
import sys
import os
import subprocess
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QMessageBox

APP_VERSION = "v1.0.0" 

API_URL = "https://api.github.com/repos/krutoychel24/hru-hru-launcher/releases/latest"

DOWNLOAD_URL_TEMPLATE = "https://github.com/krutoychel24/hru-hru-launcher/releases/download/{tag}/{filename}"


class UpdateWorker(QThread):
    """
    Проверяет, скачивает и устанавливает обновление, как вы и предложили.
    """
    update_check_finished = Signal(str, str) 
    error_occurred = Signal(str)             
    download_finished = Signal(str)         

    def run(self):
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status() 
            
            data = response.json()
            latest_version_tag = data['tag_name']

            if latest_version_tag.lower() != APP_VERSION.lower():
                release_notes = data['body'] 
                self.update_check_finished.emit(latest_version_tag, release_notes)
            else:
                pass

        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"Ошибка сети: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Произошла ошибка: {e}")

    def download_update(self, version_tag, asset_name="HruHruLauncher.exe"):
        """Метод для скачивания файла. Запускается после подтверждения пользователя."""
        try:
            download_url = DOWNLOAD_URL_TEMPLATE.format(tag=version_tag, filename=asset_name)

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            new_exe_path = os.path.join(os.getcwd(), f"{asset_name}.new")
            with open(new_exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.download_finished.emit(new_exe_path)

        except Exception as e:
            self.error_occurred.emit(f"Ошибка при скачивании: {e}")


def install_update_and_restart(new_path):
    """
    Создает и запускает .bat скрипт для замены файла и перезапуска.
    Этот трюк нужен, потому что работающий exe не может заменить сам себя в Windows.
    """
    current_exe = sys.executable
    current_exe_name = os.path.basename(current_exe)
    
    bat_script = f"""
@echo off
echo Обновление HruHru Launcher...
timeout /t 2 /nobreak > NUL
taskkill /f /im {current_exe_name} > NUL
del "{current_exe}"
rename "{new_path}" "{current_exe_name}"
echo Готово! Запускаем обновленный лаунчер...
start "" "{current_exe}"
del "%~f0"
"""
    updater_bat_path = os.path.join(os.getcwd(), "updater.bat")
    with open(updater_bat_path, "w") as f:
        f.write(bat_script)
        
    subprocess.Popen(updater_bat_path, shell=True)
    sys.exit(0) 