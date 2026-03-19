# hru_hru_launcher/ui/widgets/mod_list_item.py

import requests
from functools import partial
from PySide6.QtCore import Qt, QThread, Signal, QSize, QRect
from PySide6.QtGui import QPixmap, QPainter, QColor, QPainterPath, QBrush, QPen
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                               QPushButton, QStackedLayout, QProgressBar,
                               QGraphicsDropShadowEffect)


_active_loaders = set()


def format_downloads(count: int) -> str:
    """Format download count: 1200000 -> '1.2M', 12500 -> '12.5K'"""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


class ImageLoaderWorker(QThread):
    image_ready = Signal(QPixmap)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self._should_stop = False
        self.finished.connect(self.deleteLater)

    def run(self):
        pixmap_result = QPixmap()
        try:
            if self._should_stop:
                return
            headers = {'User-Agent': 'HruHruLauncher/2.0 (ImageLoader)'}
            response = requests.get(self.url, stream=True, timeout=10, headers=headers)
            if self._should_stop:
                return
            response.raise_for_status()
            pixmap = QPixmap()
            if pixmap.loadFromData(response.content):
                pixmap_result = pixmap
        except (requests.RequestException, Exception):
            pass
        finally:
            if not self._should_stop:
                self.image_ready.emit(pixmap_result)

    def stop(self):
        self._should_stop = True


class RoundedImageLabel(QLabel):
    """A QLabel that clips its pixmap to a rounded rectangle."""
    def __init__(self, size=56, radius=10, parent=None):
        super().__init__(parent)
        self._size = size
        self._radius = radius
        self._pixmap = None
        self.setFixedSize(size, size)

    def setRoundedPixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap.scaled(self._size, self._size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pixmap:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(QRect(0, 0, self._size, self._size), self._radius, self._radius)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, self._pixmap)


class ModListItemWidget(QWidget):
    install_requested = Signal(dict)
    page_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, mod_data, lang_dict, is_installed=False, game_version=None, parent=None):
        super().__init__(parent)
        self.mod_data = mod_data
        self.lang_dict = lang_dict
        self.is_installed = is_installed
        self.game_version = game_version
        self.image_loader = None
        self._is_being_destroyed = False

        self.setObjectName("modCard")
        self.setup_ui()
        self._apply_card_style(hovered=False)

    def setup_ui(self):
        self.setMinimumHeight(96)
        self.setCursor(Qt.PointingHandCursor)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(0)

        # Inner card container
        self._card = QWidget(self)
        self._card.setObjectName("modCardInner")
        self._card.setAttribute(Qt.WA_StyledBackground, True)
        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(14)

        # ── Icon ──────────────────────────────────────
        self.icon_label = RoundedImageLabel(size=58, radius=10)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setObjectName("modIconLabel")
        self._set_placeholder_icon()
        card_layout.addWidget(self.icon_label)

        # ── Info ──────────────────────────────────────
        info = QVBoxLayout()
        info.setSpacing(3)

        # Row 1: title + badges
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.title_label = QLabel(self.mod_data.get("title", "Unknown Mod"))
        self.title_label.setObjectName("modTitle")
        title_row.addWidget(self.title_label)

        if self.game_version:
            badge = QLabel(self.game_version)
            badge.setObjectName("versionBadge")
            title_row.addWidget(badge)

        title_row.addStretch()

        # Row 2: author
        self.author_label = QLabel(f"by {self.mod_data.get('author', 'Unknown')}")
        self.author_label.setObjectName("modAuthor")

        # Row 3: description
        desc = self.mod_data.get("description", "")
        self.desc_label = QLabel(desc)
        self.desc_label.setObjectName("modDescription")
        self.desc_label.setWordWrap(True)

        # Row 4: stats
        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)
        downloads = self.mod_data.get("downloads", 0)
        follows = self.mod_data.get("follows", 0)
        self.stats_label = QLabel(f"⬇ {format_downloads(downloads)}   ♥ {format_downloads(follows)}")
        self.stats_label.setObjectName("modStats")
        stats_row.addWidget(self.stats_label)
        stats_row.addStretch()

        info.addLayout(title_row)
        info.addWidget(self.author_label)
        info.addWidget(self.desc_label, 1)
        info.addLayout(stats_row)

        card_layout.addLayout(info, 1)

        # ── Action area ───────────────────────────────
        action = QVBoxLayout()
        action.setAlignment(Qt.AlignCenter)
        action.setSpacing(6)

        self.button_stack = QStackedLayout()

        self.install_button = QPushButton(self.lang_dict.get("install", "Install"))
        self.install_button.setObjectName("modInstallButton")
        self.install_button.setFixedSize(100, 36)
        self.install_button.clicked.connect(partial(self.install_requested.emit, self.mod_data))

        self.delete_button = QPushButton(self.lang_dict.get("delete", "Delete"))
        self.delete_button.setObjectName("modDeleteButton")
        self.delete_button.setFixedSize(100, 36)
        self.delete_button.clicked.connect(partial(self.delete_requested.emit, self.mod_data))

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(100, 36)
        self.progress_bar.setTextVisible(True)

        self.button_stack.addWidget(self.install_button)
        self.button_stack.addWidget(self.delete_button)
        self.button_stack.addWidget(self.progress_bar)

        modrinth_btn = QPushButton("Modrinth ↗")
        modrinth_btn.setObjectName("modrinthLinkButton")
        modrinth_btn.setFixedSize(100, 26)
        modrinth_btn.clicked.connect(partial(self.page_requested.emit, self.mod_data))

        action.addLayout(self.button_stack)
        action.addWidget(modrinth_btn, 0, Qt.AlignCenter)
        card_layout.addLayout(action)

        outer.addWidget(self._card)
        self.update_view()
        self.load_icon()

    def _apply_card_style(self, hovered=False):
        bg  = "rgba(255,255,255,0.07)" if hovered else "rgba(255,255,255,0.04)"
        bdr = "rgba(255,255,255,0.14)" if hovered else "rgba(255,255,255,0.08)"
        self.setStyleSheet(f"""
            #modCardInner {{
                background: {bg};
                border-radius: 14px;
                border: 1px solid {bdr};
            }}
            #modTitle {{
                font-size: 12pt;
                font-weight: bold;
                color: #f0f0ff;
            }}
            #modAuthor {{
                font-size: 9pt;
                color: #7878a0;
            }}
            #modDescription {{
                font-size: 9pt;
                color: #aaaacc;
            }}
            #modStats {{
                font-size: 9pt;
                color: #666688;
            }}
            #versionBadge {{
                background: rgba(100,120,200,0.25);
                color: #9ab4ff;
                font-size: 8pt;
                font-weight: bold;
                padding: 2px 8px;
                border-radius: 8px;
                border: 1px solid rgba(150,180,255,0.20);
            }}
            #modInstallButton {{
                background: #1DB954;
                color: #080810;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                font-size: 9pt;
            }}
            #modInstallButton:hover {{ background: #25d066; }}
            #modInstallButton:pressed {{ background: #18a048; }}
            #modDeleteButton {{
                background: rgba(239,68,68,0.80);
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 10px;
                font-size: 9pt;
            }}
            #modDeleteButton:hover {{ background: rgba(248,79,57,0.95); }}
            #modrinthLinkButton {{
                background: transparent;
                color: #7878a0;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                font-size: 8pt;
                padding: 2px 6px;
            }}
            #modrinthLinkButton:hover {{
                color: #f0f0ff;
                background: rgba(255,255,255,0.06);
            }}
            QProgressBar {{
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                background: rgba(255,255,255,0.06);
                color: white;
                font-weight: bold;
                font-size: 9pt;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: #1DB954;
                border-radius: 9px;
            }}
        """)

    def _set_placeholder_icon(self):
        self.icon_label.setText("📦")
        self.icon_label.setStyleSheet("""
            color: #555577;
            font-size: 22px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
        """)

    def load_icon(self):
        icon_url = self.mod_data.get("icon_url")
        if not icon_url:
            return
        if self.image_loader and self.image_loader.isRunning():
            self.image_loader.stop()
            try:
                self.image_loader.image_ready.disconnect(self.on_image_loaded)
            except (TypeError, RuntimeError):
                pass
        worker = ImageLoaderWorker(icon_url)
        self.image_loader = worker
        _active_loaders.add(worker)
        worker.finished.connect(lambda w=worker: _active_loaders.discard(w))
        worker.image_ready.connect(self.on_image_loaded)
        worker.start()

    def on_image_loaded(self, pixmap):
        if self._is_being_destroyed or self.image_loader is None:
            return
        if not pixmap.isNull():
            self.icon_label.setStyleSheet("")
            self.icon_label.setText("")
            self.icon_label.setRoundedPixmap(pixmap)
        try:
            self.image_loader.image_ready.disconnect(self.on_image_loaded)
        except (TypeError, RuntimeError):
            pass

    def update_view(self, is_installing=False, progress=0):
        if is_installing:
            self.button_stack.setCurrentWidget(self.progress_bar)
            self.progress_bar.setValue(progress)
        elif self.is_installed:
            self.button_stack.setCurrentWidget(self.delete_button)
        else:
            self.button_stack.setCurrentWidget(self.install_button)

    def enterEvent(self, event):
        self._apply_card_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_card_style(hovered=False)
        super().leaveEvent(event)

    def closeEvent(self, event):
        self._is_being_destroyed = True
        if self.image_loader:
            self.image_loader.stop()
            try:
                self.image_loader.image_ready.disconnect(self.on_image_loaded)
            except (TypeError, RuntimeError):
                pass
        super().closeEvent(event)