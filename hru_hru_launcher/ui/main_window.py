import sys
import os
import json
import subprocess
import traceback
import logging
import shutil
import base64
from functools import partial
from pathlib import Path

import requests
from PySide6.QtCore import (Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QSize, QPoint, QUrl, QByteArray)
from PySide6.QtGui import (QFont, QFontDatabase, QIcon, QPixmap, QColor, QStandardItemModel, QStandardItem, QDesktopServices)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
                               QProgressBar, QFrame, QCheckBox, QSlider, QTabWidget, QTextEdit,
                               QButtonGroup, QRadioButton, QGraphicsDropShadowEffect, QColorDialog, QListWidget, QListWidgetItem, QMessageBox, QDialog,
                               QSizeGrip, QFileDialog)

import minecraft_launcher_lib

from .widgets import AnimatedButton
from .widgets.mod_list_item import ModListItemWidget
from . import themes
from ..core.mc_worker import MinecraftWorker
from ..core import mod_manager
from ..utils.paths import get_assets_dir
from ..config import resources, settings

# --- AUTO-UPDATE SETTINGS ---
APP_VERSION = "v1.1.2-beta"
API_URL = "https://api.github.com/repos/krutoychel24/hru-hru-launcher/releases/latest"
DOWNLOAD_URL_TEMPLATE = "https://github.com/krutoychel24/hru-hru-launcher/releases/download/{tag}/{filename}"
# --- END AUTO-UPDATE SETTINGS ---

class FixErrorDialog(QDialog):
    def __init__(self, error_title, error_desc, fix_suggestion, lang_dict, parent=None):
        super().__init__(parent)
        self.lang_dict = lang_dict
        self.old_pos = None
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
        icon_pixmap.loadFromData(resources.ALERT_ICON_SVG)
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

    def __init__(self, status_info, fonts, parent=None):
        super().__init__(parent)
        self.status_info = status_info
        self.fonts = fonts
        
        self.icons = {
            "check": b"""
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#78f542" viewBox="0 0 256 256">
                <path d="M229.66,77.66l-128,128a8,8,0,0,1-11.32,0l-56-56a8,8,0,0,1,11.32-11.32L96,188.69,218.34,66.34a8,8,0,0,1,11.32,11.32Z"></path>
            </svg>
            """,
            "download": b"""
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#ff5555" viewBox="0 0 256 256">
                <path d="M208,152v48a8,8,0,0,1-8,8H56a8,8,0,0,1-8-8V152a8,8,0,0,1,16,0v40H192V152a8,8,0,0,1,16,0Zm-85.66,5.66a8,8,0,0,0,11.32,0l48-48a8,8,0,0,0-11.32-11.32L136,132.69V40a8,8,0,0,0-16,0v92.69L85.66,98.34a8,8,0,0,0-11.32,11.32Z"></path>
            </svg>
            """
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

        title_label = QLabel("Update Status")
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
        self.update_button = AnimatedButton("Update")
        self.update_button.setObjectName("updateButton")
        self.update_button.setFont(self.fonts["main"])
        self.update_button.setVisible(self.status_info["is_update_available"])
        self.update_button.clicked.connect(self.update_requested.emit)
        
        close_button = AnimatedButton("Close")
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
            #updateDialogContainer {{
                background-color: #282a36;
                border-radius: 10px;
                border: 1px solid #44475a;
            }}
            #updateDialogTitle {{
                color: #f8f8f2;
            }}
            #updateDialogMessage {{
                color: #bd93f9;
            }}
            QPushButton {{ outline: none; }}
            #updateButton, #closeButton {{
                color: #f8f8f2;
                padding: 8px 16px;
                border-radius: 5px;
            }}
            #updateButton {{
                background-color: {accent};
            }}
            #closeButton {{
                background-color: #6272a4;
            }}
        """)

class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(resources.LANGUAGES[self.parent_window.current_language].get("advanced_settings", "Advanced Settings"))
        self.setMinimumWidth(500)

        self.jvm_args_input = QLineEdit(self.parent_window.jvm_args_input.text())
        self.jvm_args_input.setPlaceholderText("-XX:+UseG1GC -Xmx...G")
        
        self.java_path_input = QLineEdit(self.parent_window.java_path_input.text())
        self.java_path_input.setPlaceholderText("Auto")

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        jvm_args_label = QLabel(self.parent_window.jvm_args_label.text())
        jvm_args_label.setFont(self.parent_window.subtitle_font)

        java_path_label = QLabel(self.parent_window.java_path_label.text())
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

        close_button = AnimatedButton(resources.LANGUAGES[self.parent_window.current_language].get("close", "Close"))
        close_button.setObjectName("closeButton")
        close_button.setFont(self.parent_window.minecraft_font)
        close_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def accept(self):
        self.parent_window.jvm_args_input.setText(self.jvm_args_input.text())
        self.parent_window.java_path_input.setText(self.java_path_input.text())
        self.parent_window.save_settings()
        super().accept()

    def open_java_path_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Java Executable", "", "Executables (java.exe);;All files (*)")
        if file_path:
            self.java_path_input.setText(file_path)

    def apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{ background-color: #282a36; border: 1px solid #44475a; }}
            QLabel {{ color: #f8f8f2; }}
            #closeButton {{ color: #f8f8f2; padding: 8px 16px; border-radius: 5px; background-color: #6272a4; }}
        """)


class UpdateCheckWorker(QThread):
    update_found = Signal(str, str)
    up_to_date = Signal()
    error_occurred = Signal(str)

    def run(self):
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            latest_version_tag = data['tag_name']
            if latest_version_tag.lower() != APP_VERSION.lower():
                release_notes = data['body']
                self.update_found.emit(latest_version_tag, release_notes)
            else:
                self.up_to_date.emit()
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"Network error while checking for updates: {e}")
        except Exception as e:
            self.error_occurred.emit(f"An error occurred while checking for updates: {e}")

class ModSearchWorker(QThread):
    finished = Signal(list)
    def __init__(self, query, game_version, loader, sort_option, parent=None):
        super().__init__(parent)
        self.query = query
        self.game_version = game_version
        self.loader = loader
        self.sort_option = sort_option

    def run(self):
        logging.info(f"Starting mod search: query='{self.query}', version='{self.game_version}', loader='{self.loader}', sort='{self.sort_option}'")
        results = mod_manager.search_mods(self.query, self.game_version, self.loader, self.sort_option)
        logging.info(f"Mod search finished, found {len(results)} results.")
        self.finished.emit(results)


class ModDownloadWorker(QThread):
    finished = Signal(str, bool, str)
    mod_info_signal = Signal(str, dict)
    progress = Signal(str, int)

    def __init__(self, project_id, game_version, loader, minecraft_dir, lang_dict, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.game_version = game_version
        self.loader = loader
        self.minecraft_dir = minecraft_dir
        self.is_running = True
        self.lang_dict = lang_dict
        logging.info(f"[Worker {self.project_id}] Thread created.")

    def run(self):
        try:
            logging.info(f"[Worker {self.project_id}] Thread started. Beginning download.")
            self.progress.emit(self.project_id, 0)

            logging.info(f"[Worker {self.project_id}] Getting mod version info...")
            version_info = mod_manager.get_latest_mod_version(self.project_id, self.game_version, self.loader, self.lang_dict)
            if not version_info or not version_info.get("files"):
                logging.error(f"[Worker {self.project_id}] Could not find a compatible file.")
                self.finished.emit(self.project_id, False, f"Error for {self.project_id}: could not find a compatible file.")
                return

            logging.info(f"[Worker {self.project_id}] Version info retrieved. Finding primary file.")
            files = version_info.get("files", [])
            primary_file = next((f for f in files if f.get("primary")), files[0] if files else None)

            if not primary_file:
                logging.error(f"[Worker {self.project_id}] No files found in version manifest for download.")
                self.finished.emit(self.project_id, False, f"Error for {self.project_id}: no files found for download.")
                return

            file_url = primary_file["url"]
            file_name = primary_file["filename"]
            mods_folder = os.path.join(self.minecraft_dir, "mods")
            logging.info(f"[Worker {self.project_id}] Starting download of file '{file_name}' from '{file_url}'")

            def progress_handler(p):
                if self.is_running:
                    self.progress.emit(self.project_id, p)

            success = mod_manager.download_file(file_url, mods_folder, file_name, progress_handler, self.lang_dict)
            logging.info(f"[Worker {self.project_id}] File download finished with status: {success}")

            if success and self.is_running:
                file_info = {"filename": file_name, "url": file_url, "project_id": self.project_id}
                self.mod_info_signal.emit(self.project_id, file_info)
                self.finished.emit(self.project_id, True, f"Successfully downloaded {file_name}")
            elif not self.is_running:
                self.finished.emit(self.project_id, False, f"Download of {file_name} was cancelled.")
            else:
                self.finished.emit(self.project_id, False, f"Failed to download {file_name}.")

        except Exception as e:
            logging.critical(f"[Worker {self.project_id}] An unhandled exception occurred in the thread.", exc_info=True)
            self.finished.emit(self.project_id, False, f"Critical error in thread: {e}")
        finally:
            if self.is_running:
                self.progress.emit(self.project_id, 101)
            logging.info(f"[Worker {self.project_id}] Thread is finishing.")

    def stop(self):
        logging.info(f"[Worker {self.project_id}] Received stop command for thread.")
        self.is_running = False


class MinecraftLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.version_loader = None
        self.mod_search_worker = None
        self.update_check_worker = None
        self.mod_download_workers = {}
        self.mod_list_item_map = {}
        self.updater_path = None
        self.latest_version_info = None
        
        self.update_status_info = {"text": "Click to check for updates", "is_update_available": False}

        self.settings = settings.load_settings()

        self.current_language = self.settings.get("language", "en")
        self.lang_dict = resources.LANGUAGES[self.current_language]
        self.current_accent_color = self.settings.get("accent_color", "#1DB954")
        self.current_version_type = self.settings.get("version_type", "vanilla")

        self.minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()
        os.makedirs(self.minecraft_directory, exist_ok=True)
        self.installed_mods_path = os.path.join(self.minecraft_directory, "installed_mods.json")
        
        self.init_fonts()
        self.init_icons()
        self.init_ui()

        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        self.prepare_updater()
        self.update_version_display()

        self.old_pos = None
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)

    def init_fonts(self):
        assets_dir = get_assets_dir()
        font_path = os.path.join(assets_dir, "Minecraftia.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            self.minecraft_font = QFont(font_families[0], 10)
            self.title_font = QFont(font_families[0], 28, QFont.Bold)
            self.subtitle_font = QFont(font_families[0], 14)
        else:
            logging.warning("Font not found. Using default font.")
            self.minecraft_font = QFont("Arial", 10)
            self.title_font = QFont("Arial", 24, QFont.Bold)
            self.subtitle_font = QFont("Arial", 12)

    def init_icons(self):
        def create_icon(svg_data):
            pixmap = QPixmap()
            pixmap.loadFromData(svg_data)
            return QIcon(pixmap)

        self.play_icon = create_icon(resources.PLAY_ICON_SVG)
        self.settings_icon = create_icon(resources.SETTINGS_ICON_SVG)
        self.news_icon = create_icon(resources.NEWS_ICON_SVG)
        self.console_icon = create_icon(resources.CONSOLE_ICON_SVG)
        self.version_icon = create_icon(resources.VERSION_ICON_SVG)
        self.username_icon = create_icon(resources.USERNAME_ICON_SVG)
        self.mods_icon = create_icon(resources.MODS_ICON_SVG)
        self.modpacks_icon = create_icon(resources.MODPACKS_ICON_SVG)
        self.vpn_icon = create_icon(resources.VPN_ICON_SVG)
        self.installed_icon = create_icon(resources.INSTALLED_ICON_SVG)
        self.folder_icon = create_icon(base64.b64decode("PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgZmlsbD0iI2Y4ZjhmMiIgdmlld0JveD0iMCAwIDI1NiAyNTYiPjxwYXRoIGQ9Ik0yMjQsODhINzJBNzEuNzYsNzEuNzYsMCwwLDAsMTYsMTUyVjE4NGE4LDgsMCwwLDAsOCw4SDIyNGE4LDgsMCwwLDAsOC04Vjk2QTgsOCwwLDAsMCwyMjQsODhaTTQ4LDE1MkEyMy44MiwyMy44MiwwLDAsMSw3MiwxMjhoMTQ0djI0SDcyQTI0LDI0LDAsMCwxLDQ4LDE1MlpNMjE2LDEwNEgxODguMzhhNDAsNDAsMCwwLDAtNzYuNzYsMEg3MkEyMy44MiwyMy44MiwwLDAsMSw0OCwxMjguMzlWMTI4YTU1Ljc1LDU1Ljc1LDAsMCwxLC43Ny05LjA4bDEzLjE0LTQ4LjYyQTgsOCwwLDAsMSw3MCw2NEgyMDhhOCw4LDAsMCwxLDcuMSw0LjYzbDE4LjgxLDQ3QzIzOS40MSwxMjEuMjgsMjMyLDEyOCwyMjQsMTI4YTcuNzgsNy43OCwwLDAsMC0yLjE4LS4yN1YxMDRaIj48L3BhdGg+PC9zdmc+"))
        

        assets_dir = get_assets_dir()
        icon_path = os.path.join(assets_dir, "launcher-icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def init_ui(self):
        self.setWindowTitle("Hru Hru Launcher")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        if 'window_geometry' in self.settings:
            try:
                geom_data = self.settings['window_geometry'].encode('utf-8')
                self.restoreGeometry(QByteArray.fromBase64(QByteArray(geom_data)))
            except Exception as e:
                logging.error(f"Failed to restore window geometry: {e}")

        self.container = QWidget(self)
        self.container.setObjectName("container")
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.create_title_bar(main_layout)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(20, 10, 20, 10)
        self.create_main_panel(content_layout)
        self.create_tabs_panel(content_layout)
        main_layout.addLayout(content_layout)

        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.setContentsMargins(0, 0, 5, 5)
        bottom_bar_layout.addStretch()
        
        self.version_status_label = QLabel(f"{APP_VERSION}")
        self.version_status_label.setObjectName("versionStatusLabel")
        self.version_status_label.setFont(self.minecraft_font)
        self.version_status_label.setCursor(Qt.PointingHandCursor)
        self.version_status_label.mousePressEvent = lambda event: self.check_for_updates(manual=True)
        self.update_version_display()
        bottom_bar_layout.addWidget(self.version_status_label)
        
        size_grip = QSizeGrip(self)
        bottom_bar_layout.addWidget(size_grip, 0, Qt.AlignBottom | Qt.AlignRight)

        main_layout.addLayout(bottom_bar_layout)

        outer_layout = QVBoxLayout(self)
        outer_layout.addWidget(self.container)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.apply_theme()
        self.update_ui_text()
        self.populate_versions(self.current_version_type)
        self.tab_widget.setCurrentIndex(self.settings.get("last_tab", 0))

    def create_title_bar(self, main_layout):
        self.title_bar = QWidget()
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(60)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(20, 10, 20, 10)

        self.title_label = QLabel()
        self.title_label.setFont(self.title_font)
        self.title_label.setObjectName("titleLabel")
        self.glow_effect = QGraphicsDropShadowEffect(self)
        self.glow_effect.setBlurRadius(25)
        self.glow_effect.setOffset(0, 0)
        self.title_label.setGraphicsEffect(self.glow_effect)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.minimize_button = QPushButton("—")
        self.minimize_button.setObjectName("minimizeButton")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.clicked.connect(self.showMinimized)

        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(30, 30)
        self.close_button.clicked.connect(self.close)

        title_layout.addWidget(self.minimize_button)
        title_layout.addWidget(self.close_button)
        main_layout.addWidget(self.title_bar)

    def create_main_panel(self, content_layout):
        main_panel = QWidget()
        main_panel.setObjectName("mainPanel")
        main_panel.setFixedWidth(400)
        panel_layout = QVBoxLayout(main_panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)

        self.version_type_label = QLabel()
        self.version_type_label.setFont(self.subtitle_font)
        self.version_type_label.setObjectName("sectionLabel")

        self.version_type_group = QButtonGroup(self)
        self.vanilla_radio = QRadioButton()
        self.forge_radio = QRadioButton()
        self.fabric_radio = QRadioButton()

        version_type_map = {"vanilla": 0, "forge": 1, "fabric": 2}
        self.version_type_group.addButton(self.vanilla_radio, version_type_map["vanilla"])
        self.version_type_group.addButton(self.forge_radio, version_type_map["forge"])
        self.version_type_group.addButton(self.fabric_radio, version_type_map["fabric"])

        self.version_type_group.button(version_type_map.get(self.current_version_type, 0)).setChecked(True)
        self.version_type_group.idClicked.connect(self.change_version_type)

        version_type_layout = QHBoxLayout()
        version_type_layout.addWidget(self.vanilla_radio)
        version_type_layout.addWidget(self.forge_radio)
        version_type_layout.addWidget(self.fabric_radio)
        version_type_layout.addStretch()

        self.version_label = QLabel()
        self.version_label.setFont(self.subtitle_font)
        self.version_label.setObjectName("sectionLabel")
        version_layout = QHBoxLayout()
        version_icon_label = QLabel()
        version_icon_label.setPixmap(self.version_icon.pixmap(QSize(24, 24)))
        version_layout.addWidget(version_icon_label)
        version_layout.addWidget(self.version_label)
        version_layout.addStretch()

        self.version_combo = QComboBox()
        self.version_combo.setFont(self.minecraft_font)
        self.version_combo.setFixedHeight(40)
        self.version_combo.setIconSize(QSize(16, 16))

        self.username_label = QLabel()
        self.username_label.setFont(self.subtitle_font)
        self.username_label.setObjectName("sectionLabel")
        username_layout = QHBoxLayout()
        username_icon_label = QLabel()
        username_icon_label.setPixmap(self.username_icon.pixmap(QSize(24, 24)))
        username_layout.addWidget(username_icon_label)
        username_layout.addWidget(self.username_label)
        username_layout.addStretch()

        self.user_input = QLineEdit()
        self.user_input.setFont(self.minecraft_font)
        self.user_input.setFixedHeight(40)
        self.user_input.setText(self.settings.get("last_username", ""))

        self.launch_button = AnimatedButton("")
        self.launch_button.setObjectName("launchButton")
        self.launch_button.setFont(self.subtitle_font)
        self.launch_button.setIcon(self.play_icon)
        self.launch_button.setIconSize(QSize(24, 24))
        self.launch_button.setFixedHeight(50)
        self.launch_button.clicked.connect(self.start_minecraft)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(self.minecraft_font)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFixedHeight(30)

        self.error_label = QLabel("")
        self.error_label.setFont(self.minecraft_font)
        self.error_label.setObjectName("errorLabel")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)

        panel_layout.addWidget(self.version_type_label)
        panel_layout.addLayout(version_type_layout)
        panel_layout.addSpacing(20)
        panel_layout.addLayout(version_layout)
        panel_layout.addWidget(self.version_combo)
        panel_layout.addSpacing(20)
        panel_layout.addLayout(username_layout)
        panel_layout.addWidget(self.user_input)
        panel_layout.addStretch()
        panel_layout.addWidget(self.error_label)
        panel_layout.addWidget(self.progress_bar)
        panel_layout.addWidget(self.launch_button)
        
        content_layout.addWidget(main_panel)
        
    def create_tabs_panel(self, content_layout):
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.minecraft_font)
        self.tab_widget.setObjectName("tabWidget")

        self.create_news_tab()
        self.create_mods_tab()
        self.create_modpacks_tab()
        self.create_vpn_tab()
        self.create_console_tab()
        self.create_settings_tab()

        content_layout.addWidget(self.tab_widget)

    def create_settings_tab(self):
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)

        self.jvm_args_label = QLabel()
        self.jvm_args_label.setFont(self.subtitle_font)
        self.jvm_args_input = QLineEdit(self.settings.get("jvm_args", ""))
        
        self.java_path_label = QLabel()
        self.java_path_label.setFont(self.subtitle_font)
        self.java_path_input = QLineEdit(self.settings.get("java_path", ""))

        self.lang_label = QLabel()
        self.lang_label.setFont(self.subtitle_font)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Русский", "Українська"])
        lang_map = {"en": 0, "ru": 1, "uk": 2}
        self.language_combo.setCurrentIndex(lang_map.get(self.current_language, 0))
        self.language_combo.currentTextChanged.connect(self.change_language)

        self.accent_color_label = QLabel()
        self.accent_color_label.setFont(self.subtitle_font)

        self.color_picker_button = QPushButton()
        self.color_picker_button.clicked.connect(self.open_color_picker)

        self.color_preview = QLabel()
        self.color_preview.setObjectName("colorPreview")
        self.color_preview.setFixedSize(33, 33)
        self.update_color_preview()

        color_picker_layout = QHBoxLayout()
        color_picker_layout.addWidget(self.color_picker_button)
        color_picker_layout.addWidget(self.color_preview)
        color_picker_layout.addStretch()

        self.memory_label = QLabel()
        self.memory_label.setFont(self.subtitle_font)
        self.memory_slider = QSlider(Qt.Horizontal)
        self.memory_slider.setRange(1, 16)
        self.memory_slider.setValue(self.settings.get("memory", 4))
        self.memory_slider.setTickPosition(QSlider.TicksBelow)
        self.memory_slider.setTickInterval(1)
        self.memory_value_label = QLabel(f"{self.settings.get('memory', 4)} GB")
        self.memory_slider.valueChanged.connect(self.update_memory_feedback)
        self.memory_feedback_label = QLabel()
        self.memory_feedback_label.setAlignment(Qt.AlignCenter)
        self.update_memory_feedback(self.memory_slider.value())
        
        self.resolution_label = QLabel()
        self.resolution_label.setFont(self.subtitle_font)
        resolution_layout = QHBoxLayout()
        self.resolution_width_input = QLineEdit(self.settings.get("resolution_width", "1280"))
        self.resolution_width_input.setPlaceholderText("Width")
        self.resolution_height_input = QLineEdit(self.settings.get("resolution_height", "720"))
        self.resolution_height_input.setPlaceholderText("Height")
        resolution_layout.addWidget(self.resolution_width_input)
        resolution_layout.addWidget(QLabel("x"))
        resolution_layout.addWidget(self.resolution_height_input)

        self.fullscreen_checkbox = QCheckBox()
        self.fullscreen_checkbox.setChecked(self.settings.get("fullscreen", False))
        self.close_launcher_checkbox = QCheckBox()
        self.close_launcher_checkbox.setChecked(self.settings.get("close_launcher", True))

        self.advanced_settings_button = QPushButton()
        self.advanced_settings_button.setCheckable(False)
        self.advanced_settings_button.clicked.connect(self.open_advanced_settings)
        
        settings_layout.addWidget(self.lang_label)
        settings_layout.addWidget(self.language_combo)
        settings_layout.addSpacing(10)
        settings_layout.addWidget(self.accent_color_label)
        settings_layout.addLayout(color_picker_layout)
        settings_layout.addSpacing(10)
        settings_layout.addWidget(self.memory_label)
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(self.memory_slider)
        memory_layout.addWidget(self.memory_value_label)
        settings_layout.addLayout(memory_layout)
        settings_layout.addWidget(self.memory_feedback_label)
        settings_layout.addSpacing(10)
        settings_layout.addWidget(self.resolution_label)
        settings_layout.addLayout(resolution_layout)
        settings_layout.addSpacing(10)
        settings_layout.addWidget(self.fullscreen_checkbox)
        settings_layout.addWidget(self.close_launcher_checkbox)
        
        settings_layout.addStretch()
        settings_layout.addWidget(self.advanced_settings_button)
        
        self.tab_widget.addTab(settings_widget, self.settings_icon, "")

    def create_placeholder_tab(self, icon, tab_name):
        widget = QWidget()
        widget.setObjectName(tab_name)
        layout = QVBoxLayout(widget)
        lang = resources.LANGUAGES[self.current_language]
        label = QLabel(lang["wip_notice"])
        label.setObjectName("wipLabel")
        label.setFont(self.subtitle_font)
        label.setAlignment(Qt.AlignCenter)
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()
        self.tab_widget.addTab(widget, icon, "")

    def create_news_tab(self):
        self.create_placeholder_tab(self.news_icon, "news")

    def create_mods_tab(self):
        self.mods_tab_widget = QWidget()
        layout = QVBoxLayout(self.mods_tab_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        filters_layout = QHBoxLayout()
        self.mod_sort_label = QLabel()
        self.mod_sort_combo = QComboBox()
        self.mod_refresh_button = QPushButton()
        self.mod_refresh_button.clicked.connect(self.update_mod_list)
        
        filters_layout.addWidget(self.mod_sort_label)
        filters_layout.addWidget(self.mod_sort_combo)
        filters_layout.addStretch()
        filters_layout.addWidget(self.mod_refresh_button)

        self.mod_search_input = QLineEdit()
        self.mod_search_input.setObjectName("modSearchInput")
        self.mod_search_input.setFixedHeight(35)
        self.mod_search_input.returnPressed.connect(self.update_mod_list)

        self.mod_results_list = QListWidget()
        self.mod_results_list.setObjectName("modList")
        self.mod_results_list.setSpacing(5)

        self.open_mods_folder_button = QPushButton()
        self.open_mods_folder_button.setObjectName("openModsFolderButton")
        self.open_mods_folder_button.setIcon(self.mods_icon)
        self.open_mods_folder_button.setIconSize(QSize(28, 28))
        self.open_mods_folder_button.setFixedSize(44, 44)
        self.open_mods_folder_button.clicked.connect(self.open_mods_folder)

        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.addStretch()
        bottom_bar_layout.addWidget(self.open_mods_folder_button)

        layout.addLayout(filters_layout)
        layout.addWidget(self.mod_search_input)
        layout.addWidget(self.mod_results_list)
        layout.addLayout(bottom_bar_layout)

        self.tab_widget.addTab(self.mods_tab_widget, self.mods_icon, "")

    def create_modpacks_tab(self):
        widget = QWidget()
        widget.setObjectName("modpacks")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        self.modpacks_tab_label = QLabel()
        self.modpacks_tab_label.setObjectName("wipLabel")
        self.modpacks_tab_label.setFont(self.subtitle_font)
        self.modpacks_tab_label.setAlignment(Qt.AlignCenter)

        self.open_modpacks_folder_button = QPushButton()
        self.open_modpacks_folder_button.setObjectName("openModpacksFolderButton")
        self.open_modpacks_folder_button.setIcon(self.modpacks_icon)
        self.open_modpacks_folder_button.setIconSize(QSize(28, 28))
        self.open_modpacks_folder_button.setFixedSize(44, 44)
        self.open_modpacks_folder_button.clicked.connect(self.open_modpacks_folder)

        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.addStretch()
        bottom_bar_layout.addWidget(self.open_modpacks_folder_button)

        layout.addStretch()
        layout.addWidget(self.modpacks_tab_label)
        layout.addStretch()
        layout.addLayout(bottom_bar_layout)
        self.tab_widget.addTab(widget, self.modpacks_icon, "")

    def create_vpn_tab(self):
        self.create_placeholder_tab(self.vpn_icon, "vpn")

    def create_console_tab(self):
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)
        self.clear_console_button = AnimatedButton("")
        self.clear_console_button.setFont(self.minecraft_font)
        self.clear_console_button.setFixedHeight(35)
        self.clear_console_button.clicked.connect(self.clear_console)
        self.console_output = QTextEdit()
        self.console_output.setFont(QFont("Consolas", 9))
        self.console_output.setObjectName("consoleOutput")
        self.console_output.setReadOnly(True)
        console_layout.addWidget(self.clear_console_button)
        console_layout.addWidget(self.console_output)
        self.tab_widget.addTab(console_widget, self.console_icon, "")

    def prepare_updater(self):
        try:
            docs_path = Path.home() / "Documents" / "Hru Hru Studio" / "Hru Hru Launcher"
            docs_path.mkdir(parents=True, exist_ok=True)
            self.updater_path = docs_path / "updater.exe"

            if not getattr(sys, 'frozen', False):
                logging.warning("Updater preparation skipped: not running from a compiled executable.")
                return

            temp_updater_path = os.path.join(sys._MEIPASS, "updater.exe")
            
            shutil.copy2(temp_updater_path, self.updater_path)
            logging.info(f"Updater prepared at {self.updater_path}")

        except Exception as e:
            logging.error(f"Failed to prepare updater: {e}")
            QMessageBox.critical(self, "Updater Error", f"Failed to prepare the update component:\n{e}")

    def check_for_updates(self, manual=False):
        if manual:
            self.update_status_info["text"] = "Checking for updates..."
            self.update_version_display()

        self.update_check_worker = UpdateCheckWorker()
        self.update_check_worker.update_found.connect(lambda v, n: self.on_update_found(v, n, manual))
        self.update_check_worker.up_to_date.connect(lambda: self.on_up_to_date(manual))
        self.update_check_worker.error_occurred.connect(lambda e: self.on_update_error(e, manual))
        self.update_check_worker.start()

    def update_version_display(self):
        if self.update_status_info["is_update_available"]:
            self.version_status_label.setStyleSheet("color: #ff5555;")
        elif "Error" in self.update_status_info["text"]:
            self.version_status_label.setStyleSheet("color: #aaa;")
        elif "Checking" in self.update_status_info["text"]:
            self.version_status_label.setStyleSheet("color: #f1fa8c;")
        else:
            self.version_status_label.setStyleSheet("color: #50fa7b;")

    def show_update_dialog(self, event=None):
        if not self.update_check_worker or not self.update_check_worker.isRunning():
            self.check_for_updates(manual=True)
            return

        fonts = {"main": self.minecraft_font, "subtitle": self.subtitle_font}
        dialog = UpdateDialog(self.update_status_info, fonts, self)
        dialog.update_requested.connect(self.start_update_process)
        dialog.exec()

    def start_update_process(self):
        if not self.latest_version_info:
            return

        version = self.latest_version_info["version"]
        try:
            if not self.updater_path or not self.updater_path.exists():
                raise FileNotFoundError("updater.exe not found. Please try restarting the launcher.")

            download_url = DOWNLOAD_URL_TEMPLATE.format(tag=version, filename="HruHruLauncher.exe")
            main_app_path = sys.executable
            
            font_path = os.path.join(get_assets_dir(), "Minecraftia.ttf")

            creation_flags = subprocess.DETACHED_PROCESS if sys.platform == 'win32' else 0
            subprocess.Popen([str(self.updater_path), download_url, main_app_path, font_path], creationflags=creation_flags)
            
            sys.exit(0)

        except Exception as e:
            self.on_update_error(f"Failed to start updater: {e}", manual=True)
            QMessageBox.critical(self, "Updater Error", f"Failed to start the updater:\n{e}")

    def on_update_found(self, version, notes, manual):
        self.latest_version_info = {"version": version, "notes": notes}
        self.update_status_info = {
            "text": f"Update available: {version}",
            "is_update_available": True
        }
        self.update_version_display()
        if manual: self.show_update_dialog()

    def on_up_to_date(self, manual):
        self.latest_version_info = None
        self.update_status_info = {
            "text": "You have the latest version",
            "is_update_available": False
        }
        self.update_version_display()
        if manual: self.show_update_dialog()

    def on_update_error(self, error_text, manual):
        logging.error(f"Update error: {error_text}")
        self.latest_version_info = None
        self.update_status_info = {
            "text": "Error checking for updates",
            "is_update_available": False 
        }
        self.update_version_display()
        if manual: self.show_update_dialog()

    def open_folder(self, subfolder_name):
        folder_path = os.path.join(self.minecraft_directory, subfolder_name)
        os.makedirs(folder_path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def open_mods_folder(self):
        self.open_folder('mods')

    def open_modpacks_folder(self):
        self.open_folder('modpacks')

    def open_color_picker(self):
        initial_color = QColor(self.current_accent_color)
        color = QColorDialog.getColor(initial_color, self, "Select Accent Color")
        if color.isValid():
            self.current_accent_color = color.name()
            self.update_color_preview()
            self.apply_theme()
            
    def open_java_path_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Java Executable", "", "Executables (java.exe);;All files (*)")
        if file_path:
            self.java_path_input.setText(file_path)

    def update_color_preview(self):
        self.color_preview.setStyleSheet(f"background-color: {self.current_accent_color}; border: 2px solid #555555; border-radius: 8px;")

    def update_title_glow(self):
        self.glow_effect.setColor(QColor(self.current_accent_color))
        self.title_label.setGraphicsEffect(self.glow_effect)

    def save_settings(self):
        self.settings['window_geometry'] = self.saveGeometry().toBase64().data().decode('utf-8')

        current_settings = {
            "language": self.current_language,
            "memory": self.memory_slider.value(),
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "close_launcher": self.close_launcher_checkbox.isChecked(),
            "last_username": self.user_input.text(),
            "jvm_args": self.jvm_args_input.text(),
            "java_path": self.java_path_input.text(),
            "resolution_width": self.resolution_width_input.text(),
            "resolution_height": self.resolution_height_input.text(),
            "version_type": self.current_version_type,
            "last_version": self.version_combo.currentData(Qt.UserRole),
            "accent_color": self.current_accent_color,
            "last_tab": self.tab_widget.currentIndex(),
            "window_geometry": self.settings.get('window_geometry')
        }
        client_token = self.settings.get("clientToken")
        if client_token:
            current_settings["clientToken"] = client_token
        settings.save_settings(current_settings)

    def change_language(self, language_text):
        if language_text == "English":
            self.current_language = "en"
        elif language_text == "Русский":
            self.current_language = "ru"
        elif language_text == "Українська":
            self.current_language = "ua"
        self.lang_dict = resources.LANGUAGES[self.current_language]
        self.update_ui_text()

    def change_version_type(self, type_id):
        types_map = {0: "vanilla", 1: "forge", 2: "fabric"}
        self.current_version_type = types_map.get(type_id, "vanilla")
        self.populate_versions(self.current_version_type)
        self.mod_results_list.clear()
        self.mod_search_input.clear()
        self.on_tab_changed(self.tab_widget.currentIndex())

    def update_ui_text(self):
        lang = resources.LANGUAGES[self.current_language]
        self.title_label.setText(lang["title"])
        self.version_label.setText(lang["version"])
        self.username_label.setText(lang["username"])
        self.launch_button.setText(lang["launch"])
        self.user_input.setPlaceholderText(lang["enter_username"])
        self.tab_widget.setTabText(0, lang["news"])
        self.tab_widget.setTabText(1, lang["mods"])
        self.tab_widget.setTabText(2, lang["modpacks"])
        self.tab_widget.setTabText(3, lang["vpn"])
        self.tab_widget.setTabText(4, lang["console"])
        self.tab_widget.setTabText(5, lang["settings"])
        self.lang_label.setText(lang["language"])
        self.accent_color_label.setText(lang["accent_color"])
        self.color_picker_button.setText(lang["choose_color"])
        self.memory_label.setText(lang["memory"])
        self.fullscreen_checkbox.setText(lang["fullscreen"])
        self.close_launcher_checkbox.setText(lang["close_launcher"])
        self.clear_console_button.setText(lang["clear_console"])
        self.advanced_settings_button.setText(lang["advanced_settings_show"])
        self.resolution_label.setText(lang.get("resolution", "Game Resolution"))
        self.jvm_args_label.setText(lang.get("jvm_args_custom", "Custom JVM Arguments"))
        self.java_path_label.setText(lang.get("java_path", "Java Executable Path"))
        
        self.version_type_label.setText(lang["version_type"])
        self.vanilla_radio.setText(lang["vanilla"])
        self.forge_radio.setText(lang["forge"])
        self.fabric_radio.setText(lang["fabric"])
        self.update_memory_feedback(self.memory_slider.value())
        self.open_mods_folder_button.setToolTip(lang["open_mods_folder"])
        self.open_modpacks_folder_button.setToolTip(lang["open_modpacks_folder"])
        self.modpacks_tab_label.setText(lang["wip_notice"])
        self.mod_search_input.setPlaceholderText(lang["search_mods_placeholder"])
        self.mod_sort_label.setText(lang["sort_by"])
        self.mod_refresh_button.setText(lang["refresh"])
        self.mod_sort_combo.clear()
        self.mod_sort_combo.addItem(lang["downloads"], "downloads")
        self.mod_sort_combo.addItem(lang["relevance"], "relevance")
        self.mod_sort_combo.addItem(lang["newest"], "newest")
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, 'objectName') and tab.objectName() in ["news", "vpn", "modpacks"]:
                wip_label = tab.findChild(QLabel, "wipLabel")
                if wip_label:
                    wip_label.setText(lang["wip_notice"])
                    
    def apply_theme(self):
        base_style = themes.get_dark_theme(accent_color=self.current_accent_color)
        custom_style = "QPushButton { outline: none; }"
        self.setStyleSheet(base_style + custom_style)
        self.update_title_glow()

    @staticmethod
    def get_latest_versions(raw_versions):
        latest_versions = {}
        for version_str in raw_versions:
            if '-' not in version_str:
                continue
            mc_version = version_str.split('-', 1)[0]
            if mc_version not in latest_versions:
                latest_versions[mc_version] = version_str
        return list(latest_versions.values())
        
    def populate_versions(self, version_type="vanilla"):
        if self.version_loader and self.version_loader.isRunning():
            self.version_loader.quit()
            self.version_loader.wait()

        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        lang = resources.LANGUAGES[self.current_language]
        self.version_combo.addItem(lang["loading_versions"])

        class VersionLoader(QThread):
            finished = Signal(list)
            error = Signal(str)

            def __init__(self, v_type, parent=None):
                super().__init__(parent)
                self.v_type = v_type

            def run(self):
                try:
                    version_list = []
                    if self.v_type == "vanilla":
                        version_list = [v["id"] for v in minecraft_launcher_lib.utils.get_version_list() if v["type"] == "release"]
                    elif self.v_type == "forge":
                        raw_versions = minecraft_launcher_lib.forge.list_forge_versions()
                        version_list = MinecraftLauncher.get_latest_versions(raw_versions)
                    elif self.v_type == "fabric":
                        version_list = minecraft_launcher_lib.fabric.get_stable_minecraft_versions()
                    self.finished.emit(version_list)
                except Exception as e:
                    self.error.emit(str(e))

        self.version_loader = VersionLoader(version_type, self)
        self.version_loader.finished.connect(self.on_versions_loaded)
        self.version_loader.error.connect(self.on_version_load_error)
        self.version_loader.start()

    def on_versions_loaded(self, version_list):
        self.mod_results_list.clear()
        self.mod_search_input.clear()

        self.version_combo.clear()
        installed_ids = {v['id'] for v in minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_directory)}

        model = QStandardItemModel(self)
        for version_id in version_list:
            display_text = version_id
            if self.current_version_type in ["forge", "fabric"]:
                display_text = version_id.split('-')[0]

            item = QStandardItem(display_text)
            item.setData(version_id, Qt.UserRole)

            is_installed = False
            if self.current_version_type == 'forge':
                mc_ver, forge_ver_build = version_id.split('-', 1)
                for installed_id in installed_ids:
                    if 'forge' in installed_id and installed_id.startswith(mc_ver) and installed_id.endswith(forge_ver_build):
                        is_installed = True
                        break
            elif self.current_version_type == 'fabric':
                for installed_id in installed_ids:
                    if 'fabric-loader' in installed_id and version_id in installed_id:
                        is_installed = True
                        break
            else:
                is_installed = version_id in installed_ids

            if is_installed:
                item.setIcon(self.installed_icon)
            else:
                item.setData(QColor("#888888"), Qt.ForegroundRole)

            model.appendRow(item)

        self.version_combo.setModel(model)

        last_version = self.settings.get("last_version")
        if last_version:
            for i in range(model.rowCount()):
                if model.item(i).data(Qt.UserRole) == last_version:
                    self.version_combo.setCurrentIndex(i)
                    break

        self.version_combo.setEnabled(True)

    def on_version_load_error(self, error_msg):
        self.version_combo.clear()
        self.version_combo.addItem("Error loading versions")
        self.error_label.setText(f"Failed to load version list: {error_msg}")
        self.error_label.setVisible(True)
        self.log_to_console(f"Failed to load version list: {error_msg}")

    def update_mod_list(self):
        if self.mod_search_worker and self.mod_search_worker.isRunning():
            return

        query = self.mod_search_input.text()
        lang = resources.LANGUAGES[self.current_language]

        game_version_full = self.version_combo.currentData(Qt.UserRole)
        if not game_version_full:
            self.log_to_console("Select a game version to search for mods.")
            return

        game_version = game_version_full.split('-')[0]
        loader = self.current_version_type

        if loader == "vanilla":
            self.mod_results_list.clear()
            item = QListWidgetItem(lang["select_mod_loader"])
            item.setTextAlignment(Qt.AlignCenter)
            self.mod_results_list.addItem(item)
            return

        if self.mod_search_worker and self.mod_search_worker.isRunning():
            try:
                self.mod_search_worker.finished.disconnect(self.on_mod_search_finished)
            except (TypeError, RuntimeError):
                pass
        
        sort_option = self.mod_sort_combo.currentData()
        if not sort_option:
            sort_option = "downloads"

        self.mod_refresh_button.setEnabled(False)
        self.mod_results_list.clear()
        item = QListWidgetItem(lang.get("searching", "Searching..."))
        item.setTextAlignment(Qt.AlignCenter)
        self.mod_results_list.addItem(item)

        self.mod_search_worker = ModSearchWorker(query, game_version, loader, sort_option, self)
        self.mod_search_worker.finished.connect(self.on_mod_search_finished)
        self.mod_search_worker.start()

    def on_mod_search_finished(self, results):
        self.mod_results_list.clear()
        self.mod_list_item_map.clear()
        self.mod_refresh_button.setEnabled(True)
        lang = resources.LANGUAGES[self.current_language]

        if not results:
            item = QListWidgetItem(lang["no_mods_found"])
            item.setTextAlignment(Qt.AlignCenter)
            self.mod_results_list.addItem(item)
            return

        installed_mods = self.get_installed_mods_info()

        for mod_data in results:
            project_id = mod_data.get("project_id")
            is_installed = project_id in installed_mods

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 84))

            card_widget = ModListItemWidget(mod_data, lang, is_installed)
            card_widget.install_requested.connect(self.start_mod_download)
            card_widget.page_requested.connect(self.open_mod_page)
            card_widget.delete_requested.connect(self.delete_mod)

            self.mod_results_list.addItem(item)
            self.mod_results_list.setItemWidget(item, card_widget)
            self.mod_list_item_map[project_id] = card_widget

    def on_tab_changed(self, index):
        if self.tab_widget.widget(index) == self.mods_tab_widget:
            if self.mod_results_list.count() == 0:
                self.mod_search_input.clear()
                self.update_mod_list()

    def start_mod_download(self, mod_data):
        project_id = mod_data.get("project_id")
        logging.info(f"Received request to install mod: project_id='{project_id}', title='{mod_data.get('title')}'")

        if project_id in self.mod_download_workers and self.mod_download_workers[project_id].isRunning():
            logging.warning(f"Download for project_id='{project_id}' is already in progress.")
            return

        self.log_to_console(f"Starting download process for '{mod_data.get('title')}'...")
        logging.info(f"Starting download process for '{mod_data.get('title')}'...")

        game_version_full = self.version_combo.currentData(Qt.UserRole)
        if not game_version_full:
            self.log_to_console("Error: no game version selected.")
            logging.error("Failed to start download: no game version selected.")
            return
            
        game_version = game_version_full.split('-')[0]
        loader = self.current_version_type
        logging.info(f"Parameters for download: version='{game_version}', loader='{loader}'")

        worker = ModDownloadWorker(project_id, game_version, loader, self.minecraft_directory, self.lang_dict, self)
        
        worker.progress.connect(self.on_mod_download_progress)
        worker.finished.connect(self.on_mod_download_finished)
        worker.mod_info_signal.connect(self.add_installed_mod_info)
        worker.finished.connect(worker.deleteLater)

        self.mod_download_workers[project_id] = worker
        worker.start()
        logging.info(f"Thread for download project_id='{project_id}' started successfully.")

    def on_mod_download_progress(self, project_id, percentage):
        if project_id in self.mod_list_item_map:
            card_widget = self.mod_list_item_map[project_id]
            if percentage > 100:
                card_widget.update_view(is_installing=False)
            else:
                card_widget.update_view(is_installing=True, progress=percentage)
        else:
            logging.warning(f"Received progress for project_id='{project_id}', but widget not found in mod_list_item_map.")

    def on_mod_download_finished(self, project_id, success, message):
        logging.info(f"Received 'finished' signal for project_id='{project_id}', success={success}, message='{message}'")
        self.log_to_console(message)

        if project_id in self.mod_download_workers:
            del self.mod_download_workers[project_id]

        if project_id in self.mod_list_item_map:
            card_widget = self.mod_list_item_map[project_id]
            if success:
                card_widget.is_installed = True
            card_widget.update_view()
        else:
            logging.warning(f"Download for project_id='{project_id}' finished, but widget not found in mod_list_item_map.")

    def open_mod_page(self, mod_data):
        project_slug = mod_data.get("slug")
        if project_slug:
            url = QUrl(f"https://modrinth.com/mod/{project_slug}")
            QDesktopServices.openUrl(url)

    def get_installed_mods_info(self):
        try:
            if os.path.exists(self.installed_mods_path):
                with open(self.installed_mods_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.log_to_console(f"Error reading installed_mods.json: {e}")
            logging.error("Error reading installed_mods.json", exc_info=True)
            return {}
        return {}

    def add_installed_mod_info(self, project_id, file_info):
        installed = self.get_installed_mods_info()
        installed[project_id] = file_info
        try:
            with open(self.installed_mods_path, 'w', encoding='utf-8') as f:
                json.dump(installed, f, indent=4)
            logging.info(f"Mod info for {project_id} added to installed_mods.json")
        except IOError:
            self.log_to_console(f"Error saving the list of installed mods")
            logging.error(f"Error writing to installed_mods.json", exc_info=True)

    def remove_installed_mod_info(self, project_id):
        installed = self.get_installed_mods_info()
        if project_id in installed:
            del installed[project_id]
            try:
                with open(self.installed_mods_path, 'w', encoding='utf-8') as f:
                    json.dump(installed, f, indent=4)
                logging.info(f"Mod info for {project_id} removed from installed_mods.json")
            except IOError:
                self.log_to_console(f"Error saving the list of installed mods")
                logging.error(f"Error writing to installed_mods.json", exc_info=True)

    def delete_mod(self, mod_data):
        project_id = mod_data.get("project_id")
        installed_mods = self.get_installed_mods_info()
        logging.info(f"Request to delete mod {project_id}")

        if project_id in installed_mods:
            file_name = installed_mods[project_id].get("filename")
            if file_name:
                file_path = os.path.join(self.minecraft_directory, "mods", file_name)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        self.log_to_console(f"Deleted mod file: {file_name}")
                        logging.info(f"Deleted mod file: {file_path}")
                    except OSError:
                        self.log_to_console(f"Error deleting file {file_name}")
                        logging.error(f"Error deleting file {file_path}", exc_info=True)
                else:
                    self.log_to_console(f"Mod file not found, but record is being removed: {file_name}")
                    logging.warning(f"Mod file {file_path} not found for deletion, but its record will be removed.")
            else:
                self.log_to_console(f"Record for mod '{mod_data.get('title')}' is missing a filename.")
                logging.warning(f"'filename' is missing in installed_mods.json for {project_id}.")
            
            self.remove_installed_mod_info(project_id)
            
            if project_id in self.mod_list_item_map:
                card_widget = self.mod_list_item_map[project_id]
                card_widget.is_installed = False
                card_widget.update_view()
        else:
            self.log_to_console(f"Mod '{mod_data.get('title')}' not found in the list of installed mods.")
            logging.warning(f"Attempted to delete mod {project_id}, which is not listed in installed_mods.json")

    def start_minecraft(self):
        if self.worker and self.worker.isRunning():
            return

        username = self.user_input.text()
        lang = resources.LANGUAGES[self.current_language]
        if not username:
            self.error_label.setText(lang["enter_username_error"])
            self.error_label.setVisible(True)
            return

        self.launch_button.setEnabled(False)
        self.launch_button.setText(lang["launching"])
        self.progress_bar.setVisible(True)
        self.error_label.setVisible(False)
        self.tab_widget.setCurrentIndex(4)

        jvm_args_list = self.jvm_args_input.text().split()
        
        options = {
            "executablePath": self.java_path_input.text() or None,
            "jvmArguments": jvm_args_list,
            "resolutionWidth": self.resolution_width_input.text(),
            "resolutionHeight": self.resolution_height_input.text(),
        }

        selected_version = self.version_combo.currentData(Qt.UserRole)
        if not selected_version:
            self.log_to_console("Ошибка: Версия игры не выбрана!")
            self.on_launch_finished("error", {"type": "generic", "message": "Версия игры не выбрана."})
            return
            
        mod_loader = self.current_version_type if self.current_version_type != "vanilla" else None

        self.worker = MinecraftWorker(
            mc_version=selected_version,
            username=username,
            minecraft_dir=self.minecraft_directory,
            client_token=self.settings.get("clientToken"),
            memory_gb=self.memory_slider.value(),
            fullscreen=self.fullscreen_checkbox.isChecked(),
            options=options,
            lang=self.current_language,
            mod_loader=mod_loader,
        )

        self.worker.progress_update.connect(self.update_progress)
        self.worker.log_message.connect(self.log_to_console)
        self.worker.finished.connect(self.on_launch_finished)
        self.worker.start()

    def update_progress(self, current, max_val, status):
        self.progress_bar.setFormat(status)
        self.progress_bar.setMaximum(max_val)
        self.progress_bar.setValue(current)

    def on_launch_finished(self, result, details=None):
        lang = resources.LANGUAGES[self.current_language]
        self.launch_button.setEnabled(True)
        self.launch_button.setText(lang["launch"])
        self.progress_bar.setVisible(False)

        if result != "success" and details:
            error_type = details.get("type")
            self.log_to_console(f"Получена ошибка типа: {error_type}")

            if error_type == "file_corruption":
                version_id = details.get("version_id", "выбранной")
                title = lang.get("error_file_corruption_title")
                desc = lang.get("error_file_corruption_desc").format(version_id=version_id)
                fix = lang.get("error_file_corruption_fix")
                
                dialog = FixErrorDialog(title, desc, fix, lang, self)
                if dialog.exec() == QDialog.Accepted:
                    self.reinstall_version(version_id)

            elif error_type == "invalid_java_path":
                if self.java_path_input.text():
                    title = lang.get("error_java_path_title")
                    desc = lang.get("error_java_path_desc")
                    fix = lang.get("error_java_path_fix")
                    
                    dialog = FixErrorDialog(title, desc, fix, lang, self)
                    if dialog.exec() == QDialog.Accepted:
                        self.java_path_input.setText("")
                        self.save_settings()
                        self.start_minecraft()
                else:
                    title = lang.get("error_java_path_title")
                    desc = lang.get("error_manual_java_path_desc")
                    fix = lang.get("error_manual_java_path_fix")
                    dialog = FixErrorDialog(title, desc, fix, lang, self)
                    dialog.fix_button.setVisible(False)
                    dialog.cancel_button.setText("OK")
                    dialog.exec()
            
            elif error_type == "invalid_jvm_argument":
                title = lang.get("error_jvm_args_title")
                desc = lang.get("error_jvm_args_desc")
                fix = lang.get("error_jvm_args_fix")
                
                dialog = FixErrorDialog(title, desc, fix, lang, self)
                if dialog.exec() == QDialog.Accepted:
                    self.jvm_args_input.setText("")
                    self.save_settings()
                    self.start_minecraft()

            else:
                self.error_label.setText(details.get("message", lang.get("error_occurred")))
                self.error_label.setVisible(True)

        elif result != "success":
             self.error_label.setText(result)
             self.error_label.setVisible(True)

        if self.close_launcher_checkbox.isChecked() and result == "success":
            self.close()

    def reinstall_version(self, version_id):
        version_path = os.path.join(self.minecraft_directory, "versions", version_id)
        self.log_to_console(f"Начало переустановки версии {version_id}. Путь: {version_path}")
        if os.path.exists(version_path):
            try:
                shutil.rmtree(version_path)
                self.log_to_console(f"Папка версии '{version_id}' успешно удалена.")
                QMessageBox.information(self, "Успех",
                    f"Файлы версии '{version_id}' были удалены. Нажмите 'Играть', чтобы скачать их заново.",
                    QMessageBox.Ok)
                self.populate_versions(self.current_version_type)
            except Exception as e:
                self.log_to_console(f"Не удалось удалить папку версии: {e}")
                QMessageBox.critical(self, "Ошибка",
                    f"Не удалось удалить папку '{version_path}'.\nПроверьте, не запущена ли игра, или удалите ее вручную.",
                    QMessageBox.Ok)
        else:
             QMessageBox.warning(self, "Внимание",
                "Папка версии и так не найдена. Нажмите 'Играть' для установки.",
                QMessageBox.Ok)

    def log_to_console(self, message):
        self.console_output.append(message)
        logging.info(f"CONSOLE: {message}")

    def clear_console(self):
        self.console_output.clear()

    def update_memory_feedback(self, value):
        self.memory_value_label.setText(f"{value} GB")
        lang = resources.LANGUAGES[self.current_language]

        if value <= 1: text, color = lang["mem_feedback_risky"], "#E23D28"
        elif value <= 3: text, color = lang["mem_feedback_low"], "#F8B339"
        elif value <= 6: text, color = lang["mem_feedback_optimal"], self.current_accent_color
        elif value <= 8: text, color = lang["mem_feedback_good"], self.current_accent_color
        else: text, color = lang["mem_feedback_excessive"], "#F8B339"

        self.memory_feedback_label.setText(text)
        self.memory_feedback_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
    def open_advanced_settings(self):
        dialog = AdvancedSettingsDialog(self)
        dialog.exec()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def stop_all_threads(self):
        logging.info("Received command to stop all threads.")
        for worker in list(self.mod_download_workers.values()):
            if worker.isRunning():
                worker.stop()
                worker.quit()
                worker.wait(500)
        self.mod_download_workers.clear()
        
        for worker_attr in ['worker', 'version_loader', 'mod_search_worker', 'update_check_worker']:
            worker = getattr(self, worker_attr, None)
            if worker and worker.isRunning():
                worker.quit()
                worker.wait(500)
        logging.info("All threads stopped.")

    def closeEvent(self, event):
        logging.info("Application closing. Saving settings and stopping threads...")
        self.save_settings()
        self.stop_all_threads()
        event.accept()

    def show(self):
        super().show()
        self.fade_in_animation.start()