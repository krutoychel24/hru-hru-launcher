# hru_hru_launcher/ui/widgets/version_list_item.py

import math
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QCheckBox
from PySide6.QtGui import QIcon


def _loader_badge_colors(loader_name: str):
    """Return (bg_rgba, text_color) for a given loader type."""
    l = loader_name.lower()
    if l == "fabric":
        return "rgba(100,200,120,0.20)", "#7ddca0"
    if l == "forge":
        return "rgba(200,140,60,0.20)", "#e8a060"
    return "rgba(100,130,200,0.20)", "#90aae0"


class LoaderBadge(QLabel):
    def __init__(self, loader_name: str, parent=None):
        super().__init__(loader_name, parent)
        bg, fg = _loader_badge_colors(loader_name)
        self.setStyleSheet(f"""
            background: {bg};
            color: {fg};
            font-size: 8pt;
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 8px;
        """)


class VersionListItemWidget(QWidget):
    delete_requested = Signal(str)
    repair_requested = Signal(str)
    open_folder_requested = Signal(str)
    selection_changed = Signal(str, bool)

    def __init__(self, base_version, version_types, icons, lang_dict, parent=None):
        super().__init__(parent)
        self.base_version = base_version
        self.version_types = version_types
        self.icons = icons
        self.lang_dict = lang_dict
        self.init_ui()

    def get_main_icon(self):
        lower_types = [v.lower() for v in self.version_types]
        if 'fabric' in lower_types:
            return self.icons.get("fabric", self.icons["vanilla"])
        if 'forge' in lower_types:
            return self.icons.get("forge", self.icons["vanilla"])
        return self.icons["vanilla"]

    def init_ui(self):
        self.setObjectName("versionCard")
        self.setMinimumHeight(78)
        self.setAttribute(Qt.WA_StyledBackground, True)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 5, 8, 5)

        card = QWidget()
        card.setObjectName("versionCardInner")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(12)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(20, 20)
        self.checkbox.clicked.connect(self.on_selection_changed)
        card_layout.addWidget(self.checkbox)

        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(self.get_main_icon().pixmap(QSize(32, 32)))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icon_label)

        # Info
        info = QVBoxLayout()
        info.setSpacing(4)

        self.id_label = QLabel(self.base_version)
        self.id_label.setObjectName("versionIdLabel")

        badges_row = QHBoxLayout()
        badges_row.setContentsMargins(0, 0, 0, 0)
        badges_row.setSpacing(6)
        for vtype in self.version_types:
            badges_row.addWidget(LoaderBadge(vtype))

        self.size_label = QLabel(self.lang_dict.get("calculating_size_short", "Size: ..."))
        self.size_label.setObjectName("versionSizeLabel")
        badges_row.addStretch()
        badges_row.addWidget(self.size_label)

        info.addWidget(self.id_label)
        info.addLayout(badges_row)

        card_layout.addLayout(info, 1)

        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(6)

        self.open_folder_button = self._make_btn(
            self.lang_dict.get("open_folder", "Folder"), self.icons["folder"], self.open_folder)
        self.repair_button = self._make_btn(
            self.lang_dict.get("repair", "Repair"), self.icons["repair"], self.repair_version)
        self.delete_button = self._make_btn(
            self.lang_dict.get("delete", "Delete"), self.icons["delete"], self.delete_version,
            is_danger=True)

        btns.addWidget(self.open_folder_button)
        btns.addWidget(self.repair_button)
        btns.addWidget(self.delete_button)

        card_layout.addLayout(btns)
        outer.addWidget(card)

        self.setStyleSheet("""
            #versionCardInner {
                background: rgba(255,255,255,0.04);
                border-radius: 13px;
                border: 1px solid rgba(255,255,255,0.07);
            }
            #versionCardInner:hover {
                background: rgba(255,255,255,0.07);
                border: 1px solid rgba(255,255,255,0.12);
            }
            #versionIdLabel {
                font-size: 14pt;
                font-weight: bold;
                color: #f0f0ff;
            }
            #versionSizeLabel {
                font-size: 8pt;
                color: #c084fc;
            }
            QCheckBox {
                spacing: 0px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 2px solid rgba(255,255,255,0.18);
                background: rgba(255,255,255,0.05);
            }
            QCheckBox::indicator:checked {
                background: #1DB954;
                border-color: #1DB954;
            }
            .actionBtn {
                background: rgba(255,255,255,0.07);
                color: #aaaacc;
                border: 1px solid rgba(255,255,255,0.10);
                padding: 5px 10px;
                border-radius: 8px;
                font-size: 9pt;
                font-weight: bold;
            }
            .actionBtn:hover {
                background: rgba(255,255,255,0.12);
                color: #f0f0ff;
            }
            #deleteBtn {
                background: rgba(239,68,68,0.70);
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 8px;
                font-size: 9pt;
                font-weight: bold;
            }
            #deleteBtn:hover {
                background: rgba(248,79,57,0.95);
            }
        """)

    def _make_btn(self, text, icon, callback, is_danger=False):
        btn = QPushButton(text)
        if icon:
            btn.setIcon(icon)
            btn.setIconSize(QSize(14, 14))
        btn.clicked.connect(callback)
        if is_danger:
            btn.setObjectName("deleteBtn")
        else:
            btn.setProperty("class", "actionBtn")
        return btn

    def delete_version(self):
        self.delete_requested.emit(self.base_version)

    def repair_version(self):
        self.repair_requested.emit(self.base_version)

    def open_folder(self):
        self.open_folder_requested.emit(self.base_version)

    def on_selection_changed(self):
        self.selection_changed.emit(self.base_version, self.checkbox.isChecked())

    def is_selected(self):
        return self.checkbox.isChecked()

    @staticmethod
    def format_size(size_bytes):
        if size_bytes <= 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB")
        try:
            i = int(math.floor(math.log(size_bytes, 1024)))
            i = min(i, len(size_name) - 1)
            p = math.pow(1024, i)
            s = round(size_bytes / p, 1)
            return f"{s} {size_name[i]}"
        except (ValueError, IndexError):
            return "0 B"

    def update_size(self, size_bytes):
        txt = self.lang_dict.get("version_size_label", "Size: {size}").format(
            size=self.format_size(size_bytes))
        self.size_label.setText(txt)