# hru_hru_launcher/ui/widgets/installed_mod_list_item.py

import os
import requests
from PySide6.QtCore import Qt, Signal, QThread, QRect, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QPixmap, QFont, QPainter, QPainterPath, QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton


class ImageLoaderWorker(QThread):
    image_ready = Signal(QPixmap)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.finished.connect(self.deleteLater)

    def run(self):
        pixmap = QPixmap()
        try:
            headers = {'User-Agent': 'HruHruLauncher/2.0 (ImageLoader)'}
            response = requests.get(self.url, stream=True, timeout=10, headers=headers)
            response.raise_for_status()
            if pixmap.loadFromData(response.content):
                self.image_ready.emit(pixmap)
                return
        except (requests.RequestException, Exception):
            pass
        self.image_ready.emit(QPixmap())


class ToggleSwitch(QPushButton):
    """iOS-style toggle switch widget."""

    def __init__(self, checked=True, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(48, 26)
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        self.toggled.connect(lambda: self._update_style())

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background: #1DB954;
                    border-radius: 13px;
                    border: none;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.12);
                    border-radius: 13px;
                    border: none;
                }
            """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 255, 255, 220))
        painter.setPen(Qt.NoPen)
        if self.isChecked():
            x = self.width() - 22
        else:
            x = 4
        painter.drawEllipse(x, 3, 20, 20)


class RoundedIconLabel(QLabel):
    def __init__(self, size=52, radius=9, parent=None):
        super().__init__(parent)
        self._sz = size
        self._r = radius
        self._px = None
        self.setFixedSize(size, size)

    def setRoundedPixmap(self, pixmap: QPixmap):
        self._px = pixmap.scaled(self._sz, self._sz, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._px:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(QRect(0, 0, self._sz, self._sz), self._r, self._r)
            p.setClipPath(path)
            p.drawPixmap(0, 0, self._px)


class InstalledModListItemWidget(QWidget):
    delete_requested = Signal(str)
    toggle_requested = Signal(str, bool)

    def __init__(self, mod_info, lang_dict, main_font=None, bold_font=None, parent=None):
        super().__init__(parent)
        self.mod_info = mod_info
        self.filepath = mod_info.get("filepath", "")
        self.image_loader = None
        self.lang_dict = lang_dict
        self.main_font = main_font or QFont()
        self.bold_font = bold_font or QFont()
        self._is_enabled = mod_info.get("enabled", True)

        self.setObjectName("installedModCard")
        self.setup_ui()
        self._apply_style()
        self.load_icon()

    def setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 5, 8, 5)

        self._card = QWidget(self)
        self._card.setObjectName("installedCardInner")
        self._card.setAttribute(Qt.WA_StyledBackground, True)
        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(12)

        # ── Icon ──────
        self.icon_label = RoundedIconLabel(size=52, radius=9)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self._set_placeholder_icon()
        card_layout.addWidget(self.icon_label)

        # ── Info ──────
        info = QVBoxLayout()
        info.setSpacing(2)

        name_font = QFont(self.bold_font)
        name_font.setPointSize(11)
        self.name_label = QLabel(self.mod_info.get("name", "Unknown Mod"))
        self.name_label.setObjectName("instModName")
        self.name_label.setFont(name_font)

        detail_font = QFont(self.main_font)
        detail_font.setPointSize(8)

        game_ver_text = self.lang_dict.get("for_mc", "MC:")
        self.version_label = QLabel(f"{game_ver_text} {self.mod_info.get('game_version', '?')}")
        self.version_label.setObjectName("instModDetail")
        self.version_label.setFont(detail_font)

        author_text = self.lang_dict.get("author", "by")
        self.author_label = QLabel(f"{author_text} {self.mod_info.get('author', 'Unknown')}")
        self.author_label.setObjectName("instModDetail")
        self.author_label.setFont(detail_font)

        file_font = QFont(self.main_font)
        file_font.setPointSize(7)
        basename = os.path.basename(self.filepath) if self.filepath else ""
        self.filename_label = QLabel(basename)
        self.filename_label.setObjectName("instModFilename")
        self.filename_label.setFont(file_font)

        info.addWidget(self.name_label)
        info.addWidget(self.author_label)
        info.addWidget(self.version_label)
        info.addWidget(self.filename_label)

        card_layout.addLayout(info, 1)

        # ── Actions ───
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.toggle_switch = ToggleSwitch(checked=self._is_enabled)
        self.toggle_switch.toggled.connect(self.on_toggle)
        actions.addWidget(self.toggle_switch)

        delete_text = self.lang_dict.get("delete", "Delete")
        self.delete_button = QPushButton(delete_text)
        self.delete_button.setObjectName("instDeleteBtn")
        self.delete_button.setFixedHeight(30)
        self.delete_button.setFont(detail_font)
        self.delete_button.clicked.connect(lambda: self.delete_requested.emit(self.filepath))
        actions.addWidget(self.delete_button)

        card_layout.addLayout(actions)
        outer.addWidget(self._card)

    def _set_placeholder_icon(self):
        self.icon_label.setText("📦")
        self.icon_label.setStyleSheet("""
            color: #555577;
            font-size: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 9px;
        """)

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
            self.icon_label.setRoundedPixmap(pixmap)

    def on_toggle(self, checked):
        self.toggle_requested.emit(self.filepath, checked)

    def _apply_style(self):
        enabled_opacity = "1.0" if self._is_enabled else "0.55"
        self.setStyleSheet(f"""
            #installedCardInner {{
                background: rgba(255,255,255,0.04);
                border-radius: 13px;
                border: 1px solid rgba(255,255,255,0.07);
            }}
            #instModName {{
                color: #f0f0ff;
            }}
            #instModDetail {{
                color: #7878a0;
            }}
            #instModFilename {{
                color: rgba(150,150,180,0.55);
                font-style: italic;
            }}
            #instDeleteBtn {{
                background: rgba(239,68,68,0.75);
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 4px 12px;
            }}
            #instDeleteBtn:hover {{
                background: rgba(248,79,57,0.95);
            }}
        """)

    def closeEvent(self, event):
        if self.image_loader and self.image_loader.isRunning():
            self.image_loader.quit()
            self.image_loader.wait()
        super().closeEvent(event)