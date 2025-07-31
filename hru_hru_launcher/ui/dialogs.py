from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QFileDialog)

from hru_hru_launcher.config import resources 
from .widgets import AnimatedButton

class FixErrorDialog(QDialog):
    def __init__(self, error_title, error_desc, fix_suggestion, lang_dict, parent=None, icon_svg=None):
        super().__init__(parent)
        self.lang_dict = lang_dict
        self.old_pos = None
        self.icon_data = icon_svg if icon_svg is not None else resources.ALERT_ICON_SVG
        self.init_ui(error_title, error_desc, fix_suggestion)
        self.apply_styles(parent.current_accent_color if parent else "#1DB954")
        
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def showEvent(self, event):
        super().showEvent(event)
        self.fade_in_animation.start()
        
    def init_ui(self, error_title, error_desc, fix_suggestion):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(480, 280)
        container = QFrame(self)
        container.setObjectName("dialogContainer")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 20)
        main_layout.setSpacing(15)
        self.header_frame = QFrame()
        self.header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        icon_pixmap = QPixmap()
        icon_pixmap.loadFromData(self.icon_data)
        icon_label = QLabel()
        icon_label.setPixmap(icon_pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        dialog_title_label = QLabel(self.lang_dict.get("error_dialog_title", "Error Detected"))
        dialog_title_label.setObjectName("dialogTitle")
        header_layout.addWidget(icon_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(dialog_title_label)
        header_layout.addStretch()
        body_layout = QVBoxLayout()
        body_layout.setContentsMargins(25, 0, 25, 0)
        body_layout.setSpacing(10)
        error_title_label = QLabel(error_title)
        error_title_label.setObjectName("errorTitle")
        error_title_label.setWordWrap(True)
        error_desc_label = QLabel(error_desc)
        error_desc_label.setObjectName("errorDesc")
        error_desc_label.setWordWrap(True)
        fix_suggestion_label = QLabel(fix_suggestion)
        fix_suggestion_label.setObjectName("fixSuggestion")
        fix_suggestion_label.setWordWrap(True)
        body_layout.addWidget(error_title_label)
        body_layout.addWidget(error_desc_label)
        body_layout.addSpacing(5)
        body_layout.addWidget(fix_suggestion_label)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(25, 0, 25, 0)
        self.cancel_button = AnimatedButton(self.lang_dict.get("cancel_button", "Cancel"))
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self.reject)
        self.fix_button = AnimatedButton(self.lang_dict.get("fix_button", "Fix It"))
        self.fix_button.setObjectName("fixButton")
        self.fix_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.fix_button)
        main_layout.addWidget(self.header_frame)
        main_layout.addLayout(body_layout)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)
        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(container)
        
    def apply_styles(self, accent_color):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            #dialogContainer {{ background-color: #282a36; border: 1px solid #44475a; border-radius: 12px; }}
            #headerFrame {{ background-color: #3a3d4c; border-bottom: 1px solid #44475a; border-top-left-radius: 12px; border-top-right-radius: 12px; }}
            #dialogTitle {{ font-size: 14pt; color: #f8f8f2; font-weight: bold; }}
            #errorTitle {{ font-size: 11pt; color: {accent_color}; font-weight: bold; }}
            #errorDesc, #fixSuggestion {{ font-size: 10pt; color: #bd93f9; }}
            #fixSuggestion {{ color: #f8f8f2; }}
            #cancelButton, #fixButton {{ color: #f8f8f2; padding: 10px 20px; border-radius: 5px; font-weight: bold; }}
            #cancelButton {{ background-color: #6272a4; }}
            #fixButton {{ background-color: {accent_color}; }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.header_frame.underMouse():
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()


class UpdateDialog(QDialog):
    update_requested = Signal()
    def __init__(self, status_info, fonts, lang_dict, parent=None):
        super().__init__(parent)
        self.status_info = status_info
        self.fonts = fonts
        self.lang_dict = lang_dict
        self.icons = {
            "check": b"""<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#78f542" viewBox="0 0 256 256"><path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path></svg>""",
            "download": b"""<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#ff5555" viewBox="0 0 256 256"><path d="M208,152v48a8,8,0,0,1-8,8H56a8,8,0,0,1-8-8V152a8,8,0,0,1,16,0v40H192V152a8,8,0,0,1,16,0Zm-85.66,5.66a8,8,0,0,0,11.32,0l48-48a8,8,0,0,0-11.32-11.32L136,132.69V40a8,8,0,0,0-16,0v92.69L85.66,98.34a8,8,0,0,0-11.32,11.32Z"></path></svg>"""
        }
        self.init_ui()
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        self.fade_in_animation.start()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 220)
        container = QFrame(self)
        container.setObjectName("updateDialogContainer")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        title_label = QLabel(self.lang_dict.get("update_status_title", "Update Status"))
        title_label.setObjectName("updateDialogTitle")
        title_label.setFont(self.fonts["subtitle"])
        info_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_pixmap = QPixmap()
        icon_data = self.icons["download"] if self.status_info["is_update_available"] else self.icons["check"]
        icon_pixmap.loadFromData(icon_data)
        icon_label.setPixmap(icon_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        message_label = QLabel(self.status_info["text"])
        message_label.setObjectName("updateDialogMessage")
        message_label.setFont(self.fonts["main"])
        message_label.setWordWrap(True)
        info_layout.addWidget(icon_label)
        info_layout.addWidget(message_label, 1)
        button_layout = QHBoxLayout()
        self.update_button = AnimatedButton(self.lang_dict.get("update_button", "Update"))
        self.update_button.setObjectName("updateButton")
        self.update_button.setFont(self.fonts["main"])
        self.update_button.setVisible(self.status_info["is_update_available"])
        self.update_button.clicked.connect(self.update_requested.emit)
        close_button = AnimatedButton(self.lang_dict.get("close", "Close"))
        close_button.setObjectName("closeButton")
        close_button.setFont(self.fonts["main"])
        close_button.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(close_button)
        main_layout.addWidget(title_label)
        main_layout.addLayout(info_layout)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)
        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(container)
        self.set_styles()

    def set_styles(self):
        accent = self.parent().current_accent_color if self.parent() else "#1DB954"
        self.setStyleSheet(f"""
            #updateDialogContainer {{ background-color: #282a36; border-radius: 10px; border: 1px solid #44475a; }}
            #updateDialogTitle {{ color: #f8f8f2; }}
            #updateDialogMessage {{ color: #bd93f9; }}
            QPushButton {{ outline: none; }}
            #updateButton, #closeButton {{ color: #f8f8f2; padding: 8px 16px; border-radius: 5px; }}
            #updateButton {{ background-color: {accent}; }}
            #closeButton {{ background-color: #6272a4; }}
        """)
        
class VersionSelectionDialog(QDialog):
    def __init__(self, title, prompt, versions, action_text, lang_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.lang_dict = lang_dict
        self.versions = versions
        self.selected_version = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(prompt))

        self.list_widget = QListWidget()
        self.list_widget.addItems(self.versions)
        layout.addWidget(self.list_widget)

        button_box = QHBoxLayout()
        ok_button = QPushButton(action_text)
        ok_button.clicked.connect(self.on_accept)
        cancel_button = QPushButton(lang_dict.get("cancel", "Cancel"))
        cancel_button.clicked.connect(self.reject)
        button_box.addStretch()
        button_box.addWidget(cancel_button)
        button_box.addWidget(ok_button)
        layout.addLayout(button_box)
        
    def on_accept(self):
        if self.list_widget.currentItem():
            self.selected_version = self.list_widget.currentItem().text()
            self.accept()
        
    def get_selected_version(self):
        return self.selected_version

class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.lang_dict = resources.LANGUAGES[self.parent_window.current_language]
        self.setWindowTitle(self.lang_dict.get("advanced_settings", "Advanced Settings"))
        self.setMinimumWidth(500)

        # --- ИСПРАВЛЕНО: Читаем данные из словаря настроек, а не из виджетов ---
        jvm_args_from_settings = self.parent_window.settings.get("jvm_args", "")
        self.jvm_args_input = QLineEdit(jvm_args_from_settings)
        self.jvm_args_input.setPlaceholderText("-XX:+UseG1GC -Xmx...G")

        java_path_from_settings = self.parent_window.settings.get("java_path", "")
        self.java_path_input = QLineEdit(java_path_from_settings)
        self.java_path_input.setPlaceholderText("Auto (Recommended)")
        
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        jvm_args_label = QLabel(self.lang_dict.get("jvm_arguments", "JVM Arguments"))
        jvm_args_label.setFont(self.parent_window.subtitle_font)

        java_path_label = QLabel(self.lang_dict.get("java_path", "Java Executable Path"))
        java_path_label.setFont(self.parent_window.subtitle_font)

        java_path_button = QPushButton()
        java_path_button.setIcon(self.parent_window.folder_icon)
        java_path_button.setFixedSize(36, 36)
        java_path_button.setIconSize(QSize(24, 24))
        java_path_button.clicked.connect(self.open_java_path_dialog)

        java_path_layout = QHBoxLayout()
        java_path_layout.addWidget(self.java_path_input)
        java_path_layout.addWidget(java_path_button)

        layout.addWidget(jvm_args_label)
        layout.addWidget(self.jvm_args_input)
        layout.addSpacing(10)
        layout.addWidget(java_path_label)
        layout.addLayout(java_path_layout)
        layout.addStretch()

        close_button = AnimatedButton(self.lang_dict.get("save_and_close", "Save & Close"))
        close_button.setObjectName("closeButton")
        close_button.setFont(self.parent_window.minecraft_font)
        close_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def accept(self):
        # --- ИСПРАВЛЕНО: Сохраняем значения напрямую в словарь настроек ---
        self.parent_window.settings['jvm_args'] = self.jvm_args_input.text()
        self.parent_window.settings['java_path'] = self.java_path_input.text()
        
        self.parent_window.save_settings() 
        
        super().accept()

    def open_java_path_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Java Executable", "", "Executables (java.exe);;All files (*)")
        if file_path:
            self.java_path_input.setText(file_path)

    def apply_styles(self):
        accent = self.parent_window.current_accent_color
        self.setStyleSheet(f"""
            QDialog {{ background-color: #282a36; border: 1px solid #44475a; }}
            QLabel {{ color: #f8f8f2; }}
            QLineEdit {{
                background-color: #44475a;
                color: #f8f8f2;
                border: 1px solid #6272a4;
                border-radius: 5px;
                padding: 8px;
                font-size: 10pt;
            }}
            QPushButton {{
                background-color: #44475a;
                border: 1px solid #6272a4;
                border-radius: 5px;
            }}
            #closeButton {{ 
                color: #282a36; 
                padding: 8px 16px; 
                border-radius: 5px; 
                background-color: {accent}; 
                font-weight: bold;
            }}
        """)