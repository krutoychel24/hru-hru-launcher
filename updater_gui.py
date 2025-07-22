import sys
import os
import requests
import subprocess
import tempfile
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QFrame
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon

class DownloadThread(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, download_url, output_path, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.output_path = output_path

    def run(self):
        try:
            self.status.emit("Connecting to server...")
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            
            with open(self.output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    if total_size > 0:
                        progress_percent = int((bytes_downloaded / total_size) * 100)
                        self.progress.emit(progress_percent)
            
            self.status.emit("Download complete. Installing...")
            self.progress.emit(100)
            self.finished.emit(True, self.output_path)

        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class UpdaterWindow(QWidget):
    def __init__(self, download_url, main_app_path):
        super().__init__()
        self.download_url = download_url
        self.main_app_path = main_app_path

        self.init_ui()
        self.start_download()

    def init_ui(self):
        self.setWindowTitle("Hru Hru Launcher Updater")
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        container = QFrame(self)
        container.setObjectName("container")
        container.setStyleSheet("""
            #container {
                background-color: #282a36;
                border-radius: 10px;
                border: 1px solid #44475a;
            }
        """)

        layout = QVBoxLayout(container)
        
        self.status_label = QLabel("Downloading update...")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setStyleSheet("color: #f8f8f2;")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #44475a;
                border-radius: 5px;
                background-color: #44475a;
            }
            QProgressBar::chunk {
                background-color: #50fa7b;
                border-radius: 5px;
            }
        """)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(container)

    def start_download(self):
        temp_dir = os.path.dirname(sys.executable)
        self.new_launcher_temp_path = os.path.join(temp_dir, "HruHruLauncher_new.exe")
        
        self.thread = DownloadThread(self.download_url, self.new_launcher_temp_path)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.status.connect(self.status_label.setText)
        self.thread.finished.connect(self.on_download_finished)
        self.thread.start()

    def on_download_finished(self, success, result_path):
        if success:
            self.status_label.setText("Installing update...")
            self.install_and_restart(result_path)
        else:
            self.status_label.setText(f"Error: {result_path}")
            
    def install_and_restart(self, new_downloaded_path):
        old_launcher_path = self.main_app_path
        
        # Create finalizer.bat in the system temporary folder
        temp_dir = tempfile.gettempdir()
        finalizer_bat_path = os.path.join(temp_dir, "hruhru_finalizer.bat")

        bat_script = f"""
@echo off
echo Finalizing update...
timeout /t 3 /nobreak > NUL

echo Removing old version...
del "{old_launcher_path}"

echo Moving new version...
move "{new_downloaded_path}" "{old_launcher_path}"

echo Starting updated launcher...
start "" "{old_launcher_path}"

echo Cleaning up...
del "%~f0"
"""
        with open(finalizer_bat_path, "w", encoding="utf-8") as f:
            f.write(bat_script)
            
        subprocess.Popen(finalizer_bat_path, shell=True)
        QApplication.instance().quit()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: updater_gui.py <download_url> <main_app_path>")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = UpdaterWindow(download_url=sys.argv[1], main_app_path=sys.argv[2])
    window.show()
    sys.exit(app.exec())