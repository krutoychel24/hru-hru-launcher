# hru_hru_launcher/ui/dialogs.py

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QLineEdit, QFileDialog, QListWidget)

from hru_hru_launcher.config import resources
from .widgets import AnimatedButton


# ─── Shared frameless dialog base ─────────────────────────────────────────────

class FramelessDialog(QDialog):
    """Base class for all frameless, draggable dialogs."""

    def __init__(self, parent=None, fixed_size=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        if fixed_size:
            self.setFixedSize(*fixed_size)
        self._drag_pos = None
        self._drag_widget = None  # subclass sets this

        self.setWindowOpacity(0)
        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(280)
        self._fade.setStartValue(0)
        self._fade.setEndValue(1)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        self._fade.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_widget and self._drag_widget.underMouse():
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._drag_pos = event.globalPosition().toPoint()

    def _base_style(self, accent_color):
        return f"""
            QDialog {{ background: transparent; }}
            #dlgContainer {{
                background: rgba(14,14,22,0.97);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 16px;
            }}
            #dlgHeader {{
                background: rgba(255,255,255,0.04);
                border-bottom: 1px solid rgba(255,255,255,0.07);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
            #dlgTitle {{
                font-size: 13pt;
                color: #f0f0ff;
                font-weight: bold;
            }}
            QLabel {{
                color: #9a9aaa;
                background: transparent;
            }}
            QLineEdit {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 10px;
                padding: 9px 14px;
                color: #FFFFFF;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent_color};
            }}
            QPushButton {{
                border: none;
                border-radius: 10px;
                padding: 9px 20px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """


# ─── Fix Error Dialog ──────────────────────────────────────────────────────────

class FixErrorDialog(FramelessDialog):
    def __init__(self, error_title, error_desc, fix_suggestion, lang_dict,
                 parent=None, icon_svg=None):
        super().__init__(parent, fixed_size=(500, 290))
        self.lang_dict = lang_dict
        accent = parent.current_accent_color if parent else "#1DB954"
        self._build_ui(error_title, error_desc, fix_suggestion, icon_svg, accent)

    def _build_ui(self, error_title, error_desc, fix_suggestion, icon_svg, accent):
        icon_data = icon_svg if icon_svg is not None else resources.ALERT_ICON_SVG

        container = QFrame(self)
        container.setObjectName("dlgContainer")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        main = QVBoxLayout(container)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # Header (draggable)
        self.header = QFrame()
        self.header.setObjectName("dlgHeader")
        self._drag_widget = self.header
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(20, 14, 20, 14)
        h_layout.setSpacing(12)

        icon_px = QPixmap()
        icon_px.loadFromData(icon_data)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon_px.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        title_lbl = QLabel(self.lang_dict.get("error_dialog_title", "Error Detected"))
        title_lbl.setObjectName("dlgTitle")

        h_layout.addWidget(icon_lbl)
        h_layout.addWidget(title_lbl)
        h_layout.addStretch()

        # Body
        body = QVBoxLayout()
        body.setContentsMargins(24, 18, 24, 10)
        body.setSpacing(8)

        err_title = QLabel(error_title)
        err_title.setWordWrap(True)
        err_title.setStyleSheet(f"color: {accent}; font-weight: bold; font-size: 11pt;")

        err_desc = QLabel(error_desc)
        err_desc.setWordWrap(True)
        err_desc.setStyleSheet("color: #aaaacc; font-size: 10pt;")

        fix_lbl = QLabel(fix_suggestion)
        fix_lbl.setWordWrap(True)
        fix_lbl.setStyleSheet("color: #d0d0f0; font-size: 10pt;")

        body.addWidget(err_title)
        body.addWidget(err_desc)
        body.addSpacing(4)
        body.addWidget(fix_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(24, 0, 24, 20)
        btn_layout.setSpacing(10)

        self.cancel_button = AnimatedButton(self.lang_dict.get("cancel_button", "Cancel"))
        self.cancel_button.setStyleSheet("background: rgba(255,255,255,0.10); color: #ccccdd;")
        self.cancel_button.clicked.connect(self.reject)

        self.fix_button = AnimatedButton(self.lang_dict.get("fix_button", "Fix It"))
        self.fix_button.setStyleSheet(f"background: {accent}; color: #0a0a0f;")
        self.fix_button.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_button)
        btn_layout.addWidget(self.fix_button)

        main.addWidget(self.header)
        main.addLayout(body)
        main.addStretch()
        main.addLayout(btn_layout)

        self.setStyleSheet(self._base_style(accent))


# ─── Update Dialog ─────────────────────────────────────────────────────────────

class UpdateDialog(FramelessDialog):
    update_requested = Signal()

    def __init__(self, status_info, fonts, lang_dict, parent=None):
        super().__init__(parent, fixed_size=(420, 230))
        self.status_info = status_info or {"is_update_available": False, "text": ""}
        self.fonts = fonts
        self.lang_dict = lang_dict
        accent = parent.current_accent_color if parent else "#1DB954"
        self._build_ui(accent)

    def _build_ui(self, accent):
        is_update = self.status_info.get("is_update_available", False)
        msg_text = self.status_info.get("text", "")

        container = QFrame(self)
        container.setObjectName("dlgContainer")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        main = QVBoxLayout(container)
        main.setContentsMargins(26, 26, 26, 22)
        main.setSpacing(18)

        self._drag_widget = container

        title = QLabel(self.lang_dict.get("update_status_title", "Update Status"))
        title.setObjectName("dlgTitle")
        title.setFont(self.fonts.get("subtitle", QFont()))

        info_row = QHBoxLayout()
        icon_label = QLabel("🔔" if is_update else "✅")
        icon_label.setStyleSheet("font-size: 30px; background: transparent;")
        icon_label.setFixedSize(44, 44)
        icon_label.setAlignment(Qt.AlignCenter)

        msg = QLabel(msg_text)
        msg.setWordWrap(True)
        msg.setFont(self.fonts.get("main", QFont()))
        msg.setStyleSheet("color: #ccccdd; font-size: 10pt;")

        info_row.addWidget(icon_label)
        info_row.addWidget(msg, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.update_button = AnimatedButton(self.lang_dict.get("update_button", "Update"))
        self.update_button.setVisible(is_update)
        self.update_button.setStyleSheet(f"background: {accent}; color: #0a0a0f;")
        self.update_button.clicked.connect(self.update_requested.emit)

        close_btn = AnimatedButton(self.lang_dict.get("close", "Close"))
        close_btn.setStyleSheet("background: rgba(255,255,255,0.10); color: #ccccdd;")
        close_btn.clicked.connect(self.close)

        btn_row.addStretch()
        btn_row.addWidget(self.update_button)
        btn_row.addWidget(close_btn)

        main.addWidget(title)
        main.addLayout(info_row)
        main.addStretch()
        main.addLayout(btn_row)

        self.setStyleSheet(self._base_style(accent))


# ─── Version Selection Dialog ──────────────────────────────────────────────────

class VersionSelectionDialog(QDialog):
    def __init__(self, title, prompt, versions, action_text, lang_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.lang_dict = lang_dict
        self.versions = versions
        self.selected_version = None
        accent = parent.current_accent_color if parent else "#1DB954"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        prompt_lbl = QLabel(prompt)
        prompt_lbl.setWordWrap(True)
        layout.addWidget(prompt_lbl)

        self.list_widget = QListWidget()
        self.list_widget.addItems(self.versions)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                color: #f0f0ff;
                outline: none;
            }}
            QListWidget::item {{ padding: 8px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {accent}; color: #0a0a0f; }}
            QListWidget::item:hover {{ background: rgba(255,255,255,0.08); }}
        """)
        layout.addWidget(self.list_widget)

        btn_box = QHBoxLayout()
        cancel_btn = QPushButton(lang_dict.get("cancel", "Cancel"))
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton(action_text)
        ok_btn.setStyleSheet(f"background: {accent}; color: #0a0a0f; font-weight: bold;")
        ok_btn.clicked.connect(self.on_accept)
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(ok_btn)
        layout.addLayout(btn_box)

        self.setStyleSheet(f"""
            QDialog {{
                background: #0e0e16;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 12px;
            }}
            QLabel {{ color: #c0c0d8; }}
            QPushButton {{
                background: rgba(255,255,255,0.08);
                color: #ccccdd;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.14); }}
        """)

    def on_accept(self):
        if self.list_widget.currentItem():
            self.selected_version = self.list_widget.currentItem().text()
            self.accept()

    def get_selected_version(self):
        return self.selected_version


# ─── Advanced Settings Dialog ──────────────────────────────────────────────────

class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.lang_dict = resources.LANGUAGES[self.parent_window.current_language]
        accent = parent.current_accent_color

        self.setWindowTitle(self.lang_dict.get("advanced_settings", "Advanced Settings"))
        self.setMinimumWidth(520)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)

        jvm_args_from_settings = self.parent_window.settings.get("jvm_args", "")
        self.jvm_args_input = QLineEdit(jvm_args_from_settings)
        self.jvm_args_input.setPlaceholderText("-XX:+UseG1GC -Xmx4G")

        java_path_from_settings = self.parent_window.settings.get("java_path", "")
        self.java_path_input = QLineEdit(java_path_from_settings)
        self.java_path_input.setPlaceholderText("Auto (Recommended)")

        self._build_ui(accent)
        self._apply_style(accent)

    def _build_ui(self, accent):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # JVM args
        jvm_lbl = QLabel(self.lang_dict.get("jvm_arguments", "JVM Arguments"))
        jvm_lbl.setFont(self.parent_window.subtitle_font)
        layout.addWidget(jvm_lbl)
        layout.addWidget(self.jvm_args_input)

        hint = QLabel("Example: -XX:+UseG1GC -XX:+UnlockExperimentalVMOptions")
        hint.setStyleSheet("color: rgba(150,150,180,0.60); font-size: 8pt; font-style: italic;")
        layout.addWidget(hint)
        layout.addSpacing(8)

        # Java path
        java_lbl = QLabel(self.lang_dict.get("java_path", "Java Executable Path"))
        java_lbl.setFont(self.parent_window.subtitle_font)
        layout.addWidget(java_lbl)

        java_row = QHBoxLayout()
        java_row.setSpacing(8)
        java_row.addWidget(self.java_path_input)

        browse_btn = QPushButton()
        browse_btn.setIcon(self.parent_window.folder_icon)
        browse_btn.setFixedSize(38, 38)
        browse_btn.setIconSize(QSize(22, 22))
        browse_btn.setToolTip("Browse for java.exe")
        browse_btn.clicked.connect(self._browse_java)
        java_row.addWidget(browse_btn)
        layout.addLayout(java_row)

        auto_hint = QLabel("Leave empty to use auto-detected Java.")
        auto_hint.setStyleSheet("color: rgba(150,150,180,0.60); font-size: 8pt; font-style: italic;")
        layout.addWidget(auto_hint)

        layout.addStretch()

        save_btn = AnimatedButton(self.lang_dict.get("save_and_close", "Save & Close"))
        save_btn.setObjectName("savePrimary")
        save_btn.setFont(self.parent_window.minecraft_font)
        save_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _apply_style(self, accent):
        self.setStyleSheet(f"""
            QDialog {{
                background: #0e0e16;
                border: 1px solid rgba(255,255,255,0.10);
            }}
            QLabel {{
                color: #d0d0e8;
                background: transparent;
            }}
            QLineEdit {{
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 10px;
                padding: 9px 14px;
                color: #FFFFFF;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QPushButton {{
                background: rgba(255,255,255,0.08);
                color: #ccccdd;
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                padding: 8px 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.14);
            }}
            #savePrimary {{
                background: {accent};
                color: #0a0a0f;
                border: none;
                padding: 10px 24px;
            }}
            #savePrimary:hover {{
                background: {accent}dd;
            }}
        """)

    def _browse_java(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Java Executable", "", "Executables (java.exe javaw.exe);;All files (*)")
        if path:
            self.java_path_input.setText(path)

    def accept(self):
        self.parent_window.settings['jvm_args'] = self.jvm_args_input.text().strip()
        self.parent_window.settings['java_path'] = self.java_path_input.text().strip()
        self.parent_window.save_settings()
        super().accept()