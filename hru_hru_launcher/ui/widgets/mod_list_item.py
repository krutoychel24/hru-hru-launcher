import requests
from functools import partial
from PySide6.QtCore import Qt, QThread, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QStackedLayout, QProgressBar, QApplication

from ...config import resources

class ImageLoaderWorker(QThread):
    finished = Signal(QPixmap)
    
    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self._should_stop = False
        
    def run(self):
        try:
            if self._should_stop:
                return
                
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(self.url, stream=True, timeout=10, headers=headers)
            
            if self._should_stop:
                return
                
            response.raise_for_status()
            pixmap = QPixmap()
            if pixmap.loadFromData(response.content):
                if not self._should_stop:
                    self.finished.emit(pixmap)
            else:
                if not self._should_stop:
                    self.finished.emit(QPixmap())
        except (requests.RequestException, Exception):
            if not self._should_stop:
                self.finished.emit(QPixmap())
    
    def stop(self):
        self._should_stop = True

class ModListItemWidget(QWidget):
    install_requested = Signal(dict)
    page_requested = Signal(dict) 
    delete_requested = Signal(dict)

    def __init__(self, mod_data, lang_dict, is_installed=False, parent=None):
        super().__init__(parent)
        self.mod_data = mod_data
        self.lang_dict = lang_dict
        self.is_installed = is_installed
        self.image_loader = None
        self._is_being_destroyed = False
        
        self.setWindowFlags(Qt.Widget)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        self.setObjectName("modCard")
        self.setStyleSheet("""
            #modCard {
                background-color: #2a2d34;
                border-radius: 8px;
                padding: 10px;
            }
            #modTitle {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
            }
            #modAuthor, #modStats {
                color: #a0a0a0;
            }
            #modDescription {
                color: #d0d0d0;
            }
            #modInstallButton, #modDeleteButton {
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                min-width: 90px;
            }
            #modInstallButton {
                background-color: #4CAF50;
                color: white;
            }
            #modInstallButton:hover { background-color: #5cb85c; }
            #modDeleteButton {
                background-color: #f44336;
                color: white;
            }
            #modDeleteButton:hover { background-color: #f65c51; }

            QProgressBar {
                border: 1px solid #444;
                border-radius: 5px;
                text-align: center;
                background-color: #3a3d44;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #5cb85c;
                border-radius: 4px;
            }
        """)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setObjectName("modIcon")
        self.set_placeholder_icon()
        main_layout.addWidget(self.icon_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.title_label = QLabel(self.mod_data.get("title", "Unknown Mod"), self)
        self.title_label.setObjectName("modTitle")
        
        self.author_label = QLabel(f"by {self.mod_data.get('author', 'Unknown')}", self)
        self.author_label.setObjectName("modAuthor")

        self.description_label = QLabel(self.mod_data.get("description", ""), self)
        self.description_label.setObjectName("modDescription")
        self.description_label.setWordWrap(True)

        stats_layout = QHBoxLayout()
        downloads = self.mod_data.get("downloads", 0)
        self.stats_label = QLabel(f"Downloads: {downloads:,}", self)
        self.stats_label.setObjectName("modStats")
        
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.author_label)
        info_layout.addWidget(self.description_label, 1)
        info_layout.addLayout(stats_layout)
        
        main_layout.addLayout(info_layout, 1)

        action_layout = QVBoxLayout()
        action_layout.setAlignment(Qt.AlignCenter) 

        self.button_stack = QStackedLayout()

        self.install_button = QPushButton(self.lang_dict.get("install", "Install"), self)
        self.install_button.setObjectName("modInstallButton")
        self.install_button.clicked.connect(partial(self.install_requested.emit, self.mod_data))

        self.delete_button = QPushButton(self.lang_dict.get("delete", "Delete"), self)
        self.delete_button.setObjectName("modDeleteButton")
        self.delete_button.clicked.connect(partial(self.delete_requested.emit, self.mod_data))

        self.progress_bar = QProgressBar(self)
        
        self.button_stack.addWidget(self.install_button)
        self.button_stack.addWidget(self.delete_button)
        self.button_stack.addWidget(self.progress_bar)
        
        action_layout.addLayout(self.button_stack)
        main_layout.addLayout(action_layout)

        self.update_view()
        self.load_icon()

    def set_placeholder_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setText("📦")
        self.icon_label.setStyleSheet("color: #888; font-size: 24px; border: 2px solid #444; border-radius: 8px;")

    def load_icon(self):
        icon_url = self.mod_data.get("icon_url")
        if icon_url:
            # Если есть уже запущенный загрузчик - останавливаем его
            if self.image_loader:
                self.cleanup_loader()
            
            # Создаем новый загрузчик
            self.image_loader = ImageLoaderWorker(icon_url, self)
            self.image_loader.finished.connect(self.on_image_loaded)
            self.image_loader.start()

    def on_image_loaded(self, pixmap):
        # Проверяем, что виджет не уничтожается
        if self._is_being_destroyed:
            return
            
        if not pixmap.isNull():
            self.icon_label.setStyleSheet("")
            self.icon_label.setText("")
            self.icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Очищаем загрузчик после использования
        self.cleanup_loader()

    def cleanup_loader(self):
        if self.image_loader:
            # Отключаем все сигналы
            self.image_loader.finished.disconnect()
            
            # Останавливаем поток
            self.image_loader.stop()
            
            # Если поток еще работает - принудительно завершаем
            if self.image_loader.isRunning():
                self.image_loader.terminate()
                # Не ждем - сразу помечаем для удаления
                QTimer.singleShot(0, lambda: self.force_cleanup_loader())
            else:
                self.image_loader.deleteLater()
                self.image_loader = None

    def force_cleanup_loader(self):
        if self.image_loader:
            # Последняя попытка - ждем немного и удаляем
            if self.image_loader.isRunning():
                self.image_loader.wait(100)  # Очень короткое ожидание
            self.image_loader.deleteLater()
            self.image_loader = None

    def update_view(self, is_installing=False, progress=0):
        if is_installing:
            self.button_stack.setCurrentWidget(self.progress_bar)
            self.progress_bar.setValue(progress)
        elif self.is_installed:
            self.button_stack.setCurrentWidget(self.delete_button)
        else:
            self.button_stack.setCurrentWidget(self.install_button)

    def showEvent(self, event):
        if self.windowFlags() & Qt.Window:
            self.setWindowFlags(Qt.Widget)
        super().showEvent(event)

    def setVisible(self, visible):
        if visible:
            if self.windowFlags() & Qt.Window:
                self.setWindowFlags(Qt.Widget)
        super().setVisible(visible)

    def closeEvent(self, event):
        self._is_being_destroyed = True
        self.cleanup_loader()
        super().closeEvent(event)
    
    def __del__(self):
        self._is_being_destroyed = True
        if hasattr(self, 'image_loader') and self.image_loader:
            self.cleanup_loader()