import os
import requests
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton

class ImageLoaderWorker(QThread):
    """
    Воркер для асинхронной загрузки изображений по URL в отдельном потоке,
    чтобы не замораживать основной интерфейс.
    """
    image_ready = Signal(QPixmap)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.finished.connect(self.deleteLater)

    def run(self):
        pixmap = QPixmap()
        try:
            headers = {'User-Agent': 'HruHruLauncher/1.0 (ImageLoader)'}
            response = requests.get(self.url, stream=True, timeout=10, headers=headers)
            response.raise_for_status()
            if pixmap.loadFromData(response.content):
                self.image_ready.emit(pixmap)
        except (requests.RequestException, Exception):
            self.image_ready.emit(QPixmap())

class InstalledModListItemWidget(QWidget):
    """
    Виджет, представляющий один установленный мод в списке на вкладке "Installed".
    """
    delete_requested = Signal(str)
    toggle_requested = Signal(str, bool)

    def __init__(self, mod_info, lang_dict, main_font=None, bold_font=None, parent=None):
        super().__init__(parent)
        self.mod_info = mod_info
        self.filepath = mod_info.get("filepath")
        self.image_loader = None
        
        self.lang_dict = lang_dict
        self.main_font = main_font or QFont()
        self.bold_font = bold_font or QFont()

        self.setObjectName("installedModCard")
        self.setup_ui()
        self.apply_styles()
        self.load_icon()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(15)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(64, 64)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.set_placeholder_icon()
        main_layout.addWidget(self.icon_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(self.mod_info.get("name", "Unknown Mod"))
        self.name_label.setObjectName("modName")
        
        game_version_text = self.lang_dict.get("for_mc", "For MC:")
        self.version_label = QLabel(f"{game_version_text} {self.mod_info.get('game_version', 'Unknown')}")
        self.version_label.setObjectName("modDetails")

        author_text = self.lang_dict.get("author", "Author:")
        self.author_label = QLabel(f"{author_text} {self.mod_info.get('author', 'Unknown')}")
        self.author_label.setObjectName("modDetails")
        
        self.filename_label = QLabel(os.path.basename(self.filepath))
        self.filename_label.setObjectName("modFilename")

        # --- ИЗМЕНЕНИЕ: Устанавливаем конкретные уменьшенные размеры шрифтов ---
        
        # Шрифт для названия мода
        title_font = QFont(self.bold_font)
        title_font.setPointSize(12) # Уменьшили с 14 до 12
        self.name_label.setFont(title_font)

        # Шрифт для деталей (версия, автор)
        details_font = QFont(self.main_font)
        details_font.setPointSize(9) # Уменьшили с 10 до 9
        self.version_label.setFont(details_font)
        self.author_label.setFont(details_font)
        
        # Шрифт для имени файла
        filename_font = QFont(self.main_font)
        filename_font.setPointSize(8) # Сделали еще меньше
        self.filename_label.setFont(filename_font)
        
        # --------------------------------------------------------------------

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.version_label)
        info_layout.addWidget(self.author_label)
        info_layout.addWidget(self.filename_label)
        
        main_layout.addLayout(info_layout, 1)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        action_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.toggle_switch = QPushButton("✓" if self.mod_info.get("enabled") else "✗")
        self.toggle_switch.setCheckable(True)
        self.toggle_switch.setChecked(self.mod_info.get("enabled"))
        self.toggle_switch.setFixedSize(50, 25)
        self.toggle_switch.setObjectName("toggleSwitch")
        self.toggle_switch.toggled.connect(self.on_toggle)

        delete_text = self.lang_dict.get("delete", "Delete")
        self.delete_button = QPushButton(delete_text)
        self.delete_button.setObjectName("deleteButton")
        # Для кнопки используем основной шрифт, чтобы она не была слишком большой
        self.delete_button.setFont(self.main_font) 
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self.filepath))

        action_layout.addWidget(self.toggle_switch)
        action_layout.addWidget(self.delete_button)

        main_layout.addLayout(action_layout)

    def set_placeholder_icon(self):
        self.icon_label.setText("📦")
        self.icon_label.setStyleSheet("color: #888; font-size: 24px; border: 2px solid #444; border-radius: 8px;")

    def load_icon(self):
        icon_url = self.mod_info.get("icon_url")
        icon_data = self.mod_info.get("icon_data")

        if icon_url:
            self.image_loader = ImageLoaderWorker(icon_url)
            self.image_loader.image_ready.connect(self.on_image_loaded)
            self.image_loader.start()
        elif icon_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(icon_data):
                self.on_image_loaded(pixmap)

    def on_image_loaded(self, pixmap):
        if not pixmap.isNull():
            self.icon_label.setStyleSheet("")
            self.icon_label.setText("")
            self.icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def on_toggle(self, checked):
        self.toggle_requested.emit(self.filepath, checked)
        self.toggle_switch.setText("✓" if checked else "✗")
        
    def closeEvent(self, event):
        if self.image_loader and self.image_loader.isRunning():
            self.image_loader.quit()
            self.image_loader.wait()
        super().closeEvent(event)

    def apply_styles(self):
        self.setStyleSheet("""
            #installedModCard { background-color: #2a2d34; border-radius: 8px; }
            #modName { color: #ffffff; }
            #modDetails { color: #a0a0a0; }
            #modFilename { color: #777; font-style: italic; }
            #deleteButton { background-color: #f44336; color: white; font-weight: bold; border: none; border-radius: 5px; padding: 5px 10px; }
            #deleteButton:hover { background-color: #f65c51; }
            #toggleSwitch { font-family: "Segoe UI Symbol"; font-weight: bold; border-radius: 12px; border: none; }
            #toggleSwitch:checked { background-color: #4CAF50; color: white; }
            #toggleSwitch:!checked { background-color: #6272a4; color: #ddd; }
        """)