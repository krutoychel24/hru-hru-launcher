# hru_hru_launcher/ui/main_window.py

import sys
import os
import json
import subprocess
import traceback
import logging
import shutil
from pathlib import Path
import psutil
from functools import partial

import requests
from PySide6.QtCore import (Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QSize, QPoint, QUrl, QByteArray)
from PySide6.QtGui import (QFont, QFontDatabase, QIcon, QPixmap, QColor, QStandardItemModel, QStandardItem, QDesktopServices)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
                               QProgressBar, QFrame, QCheckBox, QSlider, QTabWidget, QTextEdit,
                               QButtonGroup, QRadioButton, QGraphicsDropShadowEffect, QColorDialog, QListWidget, QListWidgetItem, QMessageBox,
                               QSizeGrip, QFileDialog, QDialog, QStackedWidget)

import minecraft_launcher_lib

from .widgets import AnimatedButton
from .widgets.mod_list_item import ModListItemWidget
from .widgets.installed_mod_list_item import InstalledModListItemWidget
from .widgets.version_selection_dialog import VersionSelectionDialog
from .widgets.version_list_item import VersionListItemWidget
from . import themes
from hru_hru_launcher.core.mc_worker import MinecraftWorker
from hru_hru_launcher.core import mod_manager
from hru_hru_launcher.utils.paths import get_assets_dir
from hru_hru_launcher.config import settings
from hru_hru_launcher.config import resources
from hru_hru_launcher.utils import helpers
from .dialogs import FixErrorDialog, UpdateDialog, AdvancedSettingsDialog


# --- SETTINGS ---
APP_VERSION = "v1.2.2-beta"
API_URL = "https://api.github.com/repos/krutoychel24/hru-hru-launcher/releases/latest"
DOWNLOAD_URL_TEMPLATE = "https://github.com/krutoychel24/hru-hru-launcher/releases/download/{tag}/{filename}"
MODS_PER_PAGE = 20
# --- SETTINGS ---

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
    finished = Signal(list, int)

    def __init__(self, query, game_version, loader, sort_option, lang_dict, offset, parent=None):
        super().__init__(parent)
        self.query = query
        self.game_version = game_version
        self.loader = loader
        self.sort_option = sort_option
        self.lang_dict = lang_dict
        self.offset = offset

    def run(self):
        logging.info(f"Starting mod search: query='{self.query}', offset='{self.offset}'")
        hits, total_hits = mod_manager.search_mods(
            self.query, self.game_version, self.loader, self.lang_dict, self.sort_option, self.offset
        )
        logging.info(f"Mod search finished, found {len(hits)} results out of {total_hits}.")
        self.finished.emit(hits, total_hits)


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

    def run(self):
        try:
            self.progress.emit(self.project_id, 0)
            version_info = mod_manager.get_latest_mod_version(self.project_id, self.game_version, self.loader, self.lang_dict)
            if not version_info or not version_info.get("files"):
                self.finished.emit(self.project_id, False, f"Error for {self.project_id}: could not find a compatible file.")
                return

            files = version_info.get("files", [])
            primary_file = next((f for f in files if f.get("primary")), files[0] if files else None)

            if not primary_file:
                self.finished.emit(self.project_id, False, f"Error for {self.project_id}: no files found for download.")
                return

            file_url = primary_file["url"]
            file_name = primary_file["filename"]
            mods_folder = os.path.join(self.minecraft_dir, "mods")

            def progress_handler(p):
                if self.is_running:
                    self.progress.emit(self.project_id, p)

            success = mod_manager.download_file(file_url, mods_folder, file_name, progress_handler, self.lang_dict)

            if success and self.is_running:
                file_info = {
                    "filename": file_name,
                    "url": file_url,
                    "project_id": self.project_id,
                    "game_version": self.game_version
                }
                self.mod_info_signal.emit(self.project_id, file_info)
                self.finished.emit(self.project_id, True, f"Successfully downloaded {file_name}")
            elif not self.is_running:
                self.finished.emit(self.project_id, False, f"Download of {file_name} was cancelled.")
            else:
                self.finished.emit(self.project_id, False, f"Failed to download {file_name}.")
        except Exception as e:
            self.finished.emit(self.project_id, False, f"Critical error in thread: {e}")
        finally:
            if self.is_running:
                self.progress.emit(self.project_id, 101) # Signal completion

    def stop(self):
        self.is_running = False

class LocalModsScannerWorker(QThread):
    finished = Signal(list)

    def __init__(self, mods_folder, lang_dict, installed_mods_data, parent=None):
        super().__init__(parent)
        self.mods_folder = mods_folder
        self.lang_dict = lang_dict
        self.installed_mods_data = installed_mods_data

    def run(self):
        mods = mod_manager.scan_local_mods(self.mods_folder, self.lang_dict, self.installed_mods_data)
        self.finished.emit(mods)

class VersionSizeScannerWorker(QThread):
    finished = Signal(dict, int)

    def __init__(self, versions_path, version_ids, parent=None):
        super().__init__(parent)
        self.versions_path = versions_path
        self.version_ids = version_ids

    @staticmethod
    def get_dir_size(path):
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += VersionSizeScannerWorker.get_dir_size(entry.path)
        except (NotADirectoryError, FileNotFoundError, PermissionError):
            return 0
        return total

    def run(self):
        sizes = {}
        total_size = 0
        for version_id in self.version_ids:
            if self.isInterruptionRequested():
                return
            version_path = os.path.join(self.versions_path, version_id)
            if os.path.isdir(version_path):
                size = self.get_dir_size(version_path)
                sizes[version_id] = size
                total_size += size

        if not self.isInterruptionRequested():
            self.finished.emit(sizes, total_size)


class MinecraftLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.total_system_memory = 16
        self.worker = None
        self.version_loader = None
        self.mod_search_worker = None
        self.update_check_worker = None
        self.local_mods_scanner = None
        self.version_size_scanner = None
        self.mod_download_workers = {}
        self.mod_list_item_map = {}
        self.version_widget_map = {}
        self.mod_current_page = 1
        self.mod_total_hits = 0
        self.updater_path = None
        self.latest_version_info = None
        self.grouped_versions = {}
        self.selected_versions_for_deletion = set()

        self.update_status_info = {"text": "Click to check for updates", "is_update_available": False}

        self.settings = settings.load_settings()

        self.current_language = self.settings.get("language", "en")
        self.lang_dict = resources.LANGUAGES[self.current_language]
        self.current_accent_color = self.settings.get("accent_color", "#1DB954")
        self.current_version_type = self.settings.get("version_type", "vanilla")

        self.minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()
        if self.minecraft_directory:
            os.makedirs(self.minecraft_directory, exist_ok=True)
            self.installed_mods_path = os.path.join(self.minecraft_directory, "installed_mods.json")
        else:
            self.installed_mods_path = ""
        
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
        
        self.update_pagination_controls()
        
        self.update_mod_list()
        self.refresh_installed_mods()

    def init_fonts(self):
        assets_dir = get_assets_dir()
        font_path = os.path.join(assets_dir, "Minecraftia.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            self.minecraft_font = QFont(font_families[0], 9)
            self.title_font = QFont(font_families[0], 22, QFont.Bold)
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
        self.cancel_icon = create_icon(resources.CANCEL_ICON_SVG)
        self.settings_icon = create_icon(resources.SETTINGS_ICON_SVG)
        self.news_icon = create_icon(resources.NEWS_ICON_SVG)
        self.console_icon = create_icon(resources.CONSOLE_ICON_SVG)
        self.version_icon = create_icon(resources.VERSION_ICON_SVG)
        self.username_icon = create_icon(resources.USERNAME_ICON_SVG)
        self.mods_icon = create_icon(resources.MODS_ICON_SVG)
        self.modpacks_icon = create_icon(resources.MODPACKS_ICON_SVG)
        self.vpn_icon = create_icon(resources.VPN_ICON_SVG)
        self.installed_icon = create_icon(resources.INSTALLED_ICON_SVG)
        self.folder_icon = create_icon(resources.FOLDER_ICON_SVG)
        self.manage_versions_icon = create_icon(resources.MANAGE_ICON_SVG)

        self.version_management_icons = {
            "vanilla": self.version_icon,
            "forge": create_icon(resources.FORGE_ICON_SVG),
            "fabric": create_icon(resources.FABRIC_ICON_SVG),
            "folder": self.folder_icon,
            "repair": create_icon(resources.REPAIR_ICON_SVG),
            "delete": create_icon(resources.DELETE_ICON_SVG),
        }

        assets_dir = get_assets_dir()
        icon_path = os.path.join(assets_dir, "launcher-icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def init_ui(self):
        self.setWindowTitle("Hru Hru Launcher")
        self.resize(1280, 800)
        self.setMinimumSize(1080, 700)
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
        
    def start_minecraft(self):
        if self.worker and self.worker.isRunning():
            return
        
        username = self.user_input.text()
        if not username:
            self.error_label.setText(self.lang_dict["enter_username_error"])
            self.error_label.setVisible(True)
            return

        self.launch_control_stack.setCurrentIndex(1)
        self.error_label.setVisible(False)
        self.progress_bar.setValue(0)
        
        console_widget = self.console_output.parentWidget()
        console_index = self.tab_widget.indexOf(console_widget)
        if console_index != -1:
            self.tab_widget.setCurrentIndex(console_index)
        
        jvm_args_list = self.settings.get("jvm_args", "").split()
        java_path = self.settings.get("java_path", None)
        options = {
            "executablePath": java_path,
            "jvmArguments": jvm_args_list,
            "resolutionWidth": self.resolution_width_input.text(),
            "resolutionHeight": self.resolution_height_input.text(),
        }
        selected_version = self.version_combo.currentData(Qt.UserRole)
        if not selected_version:
            self.on_launch_finished("error", {"type": "generic", "message": "Game version not selected."})
            return

        mod_loader = self.current_version_type if self.current_version_type != "vanilla" else None
        
        self.worker = MinecraftWorker(
            mc_version=selected_version, username=username, minecraft_dir=self.minecraft_directory,
            client_token=self.settings.get("clientToken"), memory_gb=self.memory_slider.value(),
            fullscreen=self.fullscreen_checkbox.isChecked(), options=options,
            lang=self.current_language, mod_loader=mod_loader,
        )
        self.worker.progress_update.connect(self.update_progress)
        self.worker.log_message.connect(self.log_to_console)
        self.worker.finished.connect(self.on_launch_finished)
        self.worker.start()
        
    def cancel_launch(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText(self.lang_dict.get("cancelling", "Cancelling..."))

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
        
        self.launch_control_stack = QStackedWidget()
        self.launch_control_stack.setFixedHeight(50)

        self.launch_button = AnimatedButton("")
        self.launch_button.setObjectName("launchButton")
        self.launch_button.setFont(self.subtitle_font)
        self.launch_button.setIcon(self.play_icon)
        self.launch_button.setIconSize(QSize(24, 24))
        self.launch_button.setFixedHeight(50)
        self.launch_button.clicked.connect(self.start_minecraft)
        self.launch_control_stack.addWidget(self.launch_button)

        progress_container = QWidget()
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(5)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(self.minecraft_font)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setFixedHeight(30)
        
        self.progress_bar.setStyleSheet(f"QProgressBar {{ text-align: center; color: #f8f8f2; border-radius: 5px; }} QProgressBar::chunk {{ background-color: {self.current_accent_color}; border-radius: 5px; }}")

        self.cancel_button = AnimatedButton("")
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.setFont(self.minecraft_font)
        self.cancel_button.setIcon(self.cancel_icon)
        self.cancel_button.setIconSize(QSize(20, 20))
        self.cancel_button.setFixedSize(120, 50)
        self.cancel_button.clicked.connect(self.cancel_launch)

        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.cancel_button)
        self.launch_control_stack.addWidget(progress_container)

        panel_layout.addWidget(self.launch_control_stack)
        content_layout.addWidget(main_panel)

    def update_progress(self, current, max_val, status):
        if max_val > 0:
            self.progress_bar.setFormat(f"{status} - %p%")
        else:
            self.progress_bar.setFormat(status)
        
        self.progress_bar.setMaximum(max_val)
        self.progress_bar.setValue(current)

    def on_launch_finished(self, result, details=None):
        lang = self.lang_dict

        self.launch_control_stack.setCurrentIndex(0)

        if result == "success":
            if self.close_launcher_checkbox.isChecked():
                self.close()
            return
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText(lang.get("cancel", "Cancel"))
        
        if result == "cancelled":
            self.log_to_console("Launch cancelled.")
            return

        if details:
            error_type = details.get("type")
            self.log_to_console(f"Launch failed. Error type: {error_type}")
            
            if error_type == "file_lock_error":
                QMessageBox.warning(self, lang.get("error_file_lock_title", "File Lock Error"),
                                    lang.get("error_file_lock_desc", "A file needed for installation is locked, possibly by an antivirus or a stuck process. Please try closing any Java processes in Task Manager and launch again."))
            elif error_type == "network_error":
                QMessageBox.critical(self, lang.get("error_network_title", "Network Error"), lang.get("error_network_desc", "Could not connect. Check your internet."))
            elif error_type == "fabric_dependency_error":
                dependency = details.get("dependency", "required mods")
                dialog = FixErrorDialog(lang["error_fabric_dependency_title"], lang["error_fabric_dependency_desc"].format(dependency=dependency), lang["error_fabric_dependency_fix"], lang, self, icon_svg=resources.DOWNLOAD_MOD_ICON_SVG)
                if dialog.exec() == QDialog.Accepted:
                    self.install_mod_dependency(dependency)
            elif error_type == "file_corruption":
                version_id = details.get("version_id", "selected")
                dialog = FixErrorDialog(lang["error_file_corruption_title"], lang["error_file_corruption_desc"].format(version_id=version_id), lang["error_file_corruption_fix"], lang, self)
                if dialog.exec() == QDialog.Accepted:
                    self.reinstall_version(version_id)
            elif error_type == "invalid_java_path":
                dialog = FixErrorDialog(lang["error_java_path_title"], lang["error_java_path_desc"], lang["error_java_path_fix"], lang, self)
                if dialog.exec() == QDialog.Accepted:
                    self.open_advanced_settings()
            elif error_type == "invalid_jvm_argument":
                dialog = FixErrorDialog(lang["error_jvm_args_title"], lang["error_jvm_args_desc"], lang["error_jvm_args_fix"], lang, self)
                if dialog.exec() == QDialog.Accepted:
                    self.open_advanced_settings()
            else:
                self.error_label.setText(details.get("message", lang["error_occurred"]))
                self.error_label.setVisible(True)
        else:
            self.error_label.setText(lang["error_occurred"])
            self.error_label.setVisible(True)

    def create_tabs_panel(self, content_layout):
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.minecraft_font)
        self.tab_widget.setObjectName("tabWidget")
        
        self.create_news_tab()
        self.create_mods_tab()
        self.create_versions_tab()
        self.create_modpacks_tab()
        self.create_vpn_tab()
        self.create_console_tab()
        self.create_settings_tab()

        content_layout.addWidget(self.tab_widget)

    def create_settings_tab(self):
        self.settings_tab_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab_widget)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)

        self.lang_label = QLabel()
        self.lang_label.setFont(self.subtitle_font)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Русский", "Українська"])
        lang_map = {"en": 0, "ru": 1, "ua": 2}
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

        try:
            self.total_system_memory = int(psutil.virtual_memory().total / (1024**3))
            self.memory_slider.setRange(1, self.total_system_memory)
        except Exception as e:
            logging.error(f"Unable to determine RAM capacity: {e}")
            self.total_system_memory = 16
            self.memory_slider.setRange(1, self.total_system_memory)

        current_mem = self.settings.get("memory", 4)
        if current_mem > self.total_system_memory:
            current_mem = self.total_system_memory
        self.memory_slider.setValue(current_mem)

        self.memory_slider.setTickPosition(QSlider.TicksBelow)
        self.memory_slider.setTickInterval(1)
        self.memory_value_label = QLabel(f"{self.memory_slider.value()} GB")
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
        
        self.tab_widget.addTab(self.settings_tab_widget, self.settings_icon, "")

    def create_placeholder_tab(self, icon, tab_name):
        widget = QWidget()
        widget.setObjectName(tab_name)
        layout = QVBoxLayout(widget)
        label = QLabel(self.lang_dict["wip_notice"])
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
        main_layout = QVBoxLayout(self.mods_tab_widget)
        main_layout.setContentsMargins(0,0,0,0)

        self.mods_sub_tabs = QTabWidget()
        self.mods_sub_tabs.setObjectName("modsSubTabs")
        main_layout.addWidget(self.mods_sub_tabs)
        
        # --- Search Tab ---
        search_widget = QWidget()
        search_layout = QVBoxLayout(search_widget)
        search_layout.setContentsMargins(10, 10, 10, 10)
        search_layout.setSpacing(10)

        filters_layout = QHBoxLayout()
        self.mod_sort_label = QLabel()
        self.mod_sort_combo = QComboBox()
        self.mod_refresh_button = QPushButton()
        self.mod_refresh_button.clicked.connect(lambda: self.update_mod_list(reset_page=True))
        
        filters_layout.addWidget(self.mod_sort_label)
        filters_layout.addWidget(self.mod_sort_combo)
        filters_layout.addStretch()
        filters_layout.addWidget(self.mod_refresh_button)

        self.mod_search_input = QLineEdit()
        self.mod_search_input.setObjectName("modSearchInput")
        self.mod_search_input.setFixedHeight(35)
        self.mod_search_input.returnPressed.connect(lambda: self.update_mod_list(reset_page=True))

        self.mod_results_list = QListWidget()
        self.mod_results_list.setObjectName("modList")
        self.mod_results_list.setSpacing(5)

        pagination_layout = QHBoxLayout()
        self.prev_page_button = QPushButton("<")
        self.prev_page_button.setFixedSize(35, 35)
        self.prev_page_button.clicked.connect(self.prev_mod_page)
        
        self.page_label = QLabel("Page 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        
        self.next_page_button = QPushButton(">")
        self.next_page_button.setFixedSize(35, 35)
        self.next_page_button.clicked.connect(self.next_mod_page)

        pagination_layout.addStretch()
        pagination_layout.addWidget(self.prev_page_button)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_page_button)
        pagination_layout.addStretch()
        
        # --- Installed Tab ---
        installed_widget = QWidget()
        installed_layout = QVBoxLayout(installed_widget)
        installed_layout.setContentsMargins(10, 10, 10, 10)
        installed_layout.setSpacing(10)

        installed_top_bar = QHBoxLayout()
        installed_top_bar.addStretch()
        
        self.refresh_installed_button = QPushButton()
        self.refresh_installed_button.clicked.connect(self.refresh_installed_mods)
        installed_top_bar.addWidget(self.refresh_installed_button)

        self.installed_mods_list = QListWidget()
        self.installed_mods_list.setObjectName("modList")
        self.installed_mods_list.setSpacing(5)
        
        # --- Common bottom bar button for both tabs ---
        open_mods_folder_button_search = QPushButton()
        open_mods_folder_button_search.setObjectName("openModsFolderButton")
        open_mods_folder_button_search.setIcon(self.mods_icon)
        open_mods_folder_button_search.setIconSize(QSize(28, 28))
        open_mods_folder_button_search.setFixedSize(44, 44)
        open_mods_folder_button_search.clicked.connect(self.open_mods_folder)

        search_bottom_bar = QHBoxLayout()
        search_bottom_bar.addLayout(pagination_layout, 1)
        search_bottom_bar.addWidget(open_mods_folder_button_search)
        
        installed_bottom_bar = QHBoxLayout()
        installed_bottom_bar.addStretch()
        open_mods_folder_button_installed = QPushButton()
        open_mods_folder_button_installed.setObjectName("openModsFolderButton")
        open_mods_folder_button_installed.setIcon(self.mods_icon)
        open_mods_folder_button_installed.setIconSize(QSize(28, 28))
        open_mods_folder_button_installed.setFixedSize(44, 44)
        open_mods_folder_button_installed.clicked.connect(self.open_mods_folder)
        installed_bottom_bar.addWidget(open_mods_folder_button_installed)


        search_layout.addLayout(filters_layout)
        search_layout.addWidget(self.mod_search_input)
        search_layout.addWidget(self.mod_results_list, 1)
        search_layout.addLayout(search_bottom_bar)
        
        installed_layout.addLayout(installed_top_bar)
        installed_layout.addWidget(self.installed_mods_list, 1)
        installed_layout.addLayout(installed_bottom_bar)

        self.mods_sub_tabs.addTab(search_widget, "")
        self.mods_sub_tabs.addTab(installed_widget, "")

        self.tab_widget.addTab(self.mods_tab_widget, self.mods_icon, "")
        self.mods_sub_tabs.currentChanged.connect(self.on_mods_sub_tab_changed)
    
    def create_versions_tab(self):
        self.versions_tab_widget = QWidget()
        versions_layout = QVBoxLayout(self.versions_tab_widget)
        versions_layout.setContentsMargins(10, 10, 10, 10)
        versions_layout.setSpacing(10)

        top_bar_layout = QHBoxLayout()
        
        self.delete_selected_versions_button = QPushButton()
        self.delete_selected_versions_button.setObjectName("deleteSelectedButton")
        self.delete_selected_versions_button.setIcon(self.version_management_icons.get("delete"))
        self.delete_selected_versions_button.clicked.connect(self.delete_selected_versions)
        self.delete_selected_versions_button.setEnabled(False)
        top_bar_layout.addWidget(self.delete_selected_versions_button)
        
        top_bar_layout.addStretch()
        
        self.refresh_versions_button = QPushButton()
        self.refresh_versions_button.clicked.connect(self.refresh_installed_versions_list)
        top_bar_layout.addWidget(self.refresh_versions_button)
        
        size_info_layout = QHBoxLayout()
        size_info_layout.setContentsMargins(0, 5, 10, 5)
        self.total_versions_size_label = QLabel()
        self.total_versions_size_label.setObjectName("totalSizeLabel")
        self.total_versions_size_label.setAlignment(Qt.AlignRight)
        size_info_layout.addStretch()
        size_info_layout.addWidget(self.total_versions_size_label)

        self.installed_versions_list = QListWidget()
        self.installed_versions_list.setObjectName("modList")
        self.installed_versions_list.setSpacing(5)

        versions_layout.addLayout(top_bar_layout)
        versions_layout.addLayout(size_info_layout)
        versions_layout.addWidget(self.installed_versions_list, 1)

        self.tab_widget.addTab(self.versions_tab_widget, self.manage_versions_icon, "")

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

    def prev_mod_page(self):
        if self.mod_current_page > 1:
            self.mod_current_page -= 1
            self.update_mod_list(reset_page=False)

    def next_mod_page(self):
        if self.mod_current_page * MODS_PER_PAGE < self.mod_total_hits:
            self.mod_current_page += 1
            self.update_mod_list(reset_page=False)

    def update_pagination_controls(self):
        self.page_label.setText(f"{self.lang_dict.get('page', 'Page')} {self.mod_current_page}")
        is_prev_enabled = self.mod_current_page > 1
        self.prev_page_button.setEnabled(is_prev_enabled)
        self.prev_page_button.setStyleSheet("opacity: 1.0;" if is_prev_enabled else "opacity: 0.4;")
        is_next_enabled = self.mod_current_page * MODS_PER_PAGE < self.mod_total_hits
        self.next_page_button.setEnabled(is_next_enabled)
        self.next_page_button.setStyleSheet("opacity: 1.0;" if is_next_enabled else "opacity: 0.4;")

    def update_mod_list(self, reset_page=True):
        if self.mod_search_worker and self.mod_search_worker.isRunning():
            return
        if reset_page:
            self.mod_current_page = 1
        query = self.mod_search_input.text()
        game_version_full = self.version_combo.currentData(Qt.UserRole)
        if not game_version_full:
            self.log_to_console("Select a game version to search for mods.")
            return
        game_version = game_version_full.split('-')[0]
        loader = self.current_version_type
        if loader == "vanilla":
            self.mod_results_list.clear()
            item = QListWidgetItem(self.lang_dict["select_mod_loader"])
            item.setTextAlignment(Qt.AlignCenter)
            self.mod_results_list.addItem(item)
            return
        sort_option = self.mod_sort_combo.currentData() or "downloads"
        offset = (self.mod_current_page - 1) * MODS_PER_PAGE
        self.mod_refresh_button.setEnabled(False)
        self.mod_results_list.clear()
        item = QListWidgetItem(self.lang_dict.get("searching", "Searching..."))
        item.setTextAlignment(Qt.AlignCenter)
        self.mod_results_list.addItem(item)
        self.mod_search_worker = ModSearchWorker(query, game_version, loader, sort_option, self.lang_dict, offset, self)
        self.mod_search_worker.finished.connect(self.on_mod_search_finished)
        self.mod_search_worker.start()

    def on_mod_search_finished(self, results, total_hits):
        self.mod_total_hits = total_hits
        self.mod_results_list.clear()
        self.mod_list_item_map.clear()
        self.mod_refresh_button.setEnabled(True)
        try:
            game_version = self.version_combo.currentData(Qt.UserRole).split('-')[0]
        except (AttributeError, IndexError):
            game_version = None
        if not results:
            item = QListWidgetItem(self.lang_dict["no_mods_found"])
            item.setTextAlignment(Qt.AlignCenter)
            self.mod_results_list.addItem(item)
        else:
            installed_mods = self.get_installed_mods_info()
            for mod_data in results:
                project_id = mod_data.get("project_id")
                is_installed = project_id in installed_mods
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 84))
                card_widget = ModListItemWidget(mod_data, self.lang_dict, is_installed, game_version)
                card_widget.install_requested.connect(self.start_mod_download)
                card_widget.page_requested.connect(self.open_mod_page)
                card_widget.delete_requested.connect(self.delete_mod)
                self.mod_results_list.addItem(item)
                self.mod_results_list.setItemWidget(item, card_widget)
                self.mod_list_item_map[project_id] = card_widget
        self.update_pagination_controls()

    def refresh_installed_mods(self):
        if self.local_mods_scanner and self.local_mods_scanner.isRunning():
            return
        mods_folder = os.path.join(self.minecraft_directory, "mods")
        self.installed_mods_list.clear()
        item = QListWidgetItem(self.lang_dict.get("scanning", "Scanning..."))
        item.setTextAlignment(Qt.AlignCenter)
        self.installed_mods_list.addItem(item)
        
        installed_data = self.get_installed_mods_info()
        self.local_mods_scanner = LocalModsScannerWorker(mods_folder, self.lang_dict, installed_data, self)
        self.local_mods_scanner.finished.connect(self.on_local_mods_scanned)
        self.local_mods_scanner.start()

    def on_local_mods_scanned(self, mods_list):
        self.installed_mods_list.clear()
        if not mods_list:
            item = QListWidgetItem(self.lang_dict.get("no_local_mods_found", "No mods found in folder."))
            item.setTextAlignment(Qt.AlignCenter)
            self.installed_mods_list.addItem(item)
            return
        
        for mod_info in sorted(mods_list, key=lambda x: x['name'].lower()):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 90))
            widget = InstalledModListItemWidget(
                mod_info, self.lang_dict, main_font=self.minecraft_font, bold_font=self.subtitle_font
                )
            widget.delete_requested.connect(self.handle_mod_delete)
            widget.toggle_requested.connect(self.handle_mod_toggle)
            self.installed_mods_list.addItem(item)
            self.installed_mods_list.setItemWidget(item, widget)

    def handle_mod_delete(self, filepath):
        filename = os.path.basename(filepath)
        
        project_id_to_update = None
        installed_json = self.get_installed_mods_info()
        for pid, info in installed_json.items():
            if info.get("filename") == filename:
                project_id_to_update = pid
                break

        try:
            os.remove(filepath)
            self.log_to_console(f"Deleted mod file: {filename}")
            
            if project_id_to_update:
                self.remove_installed_mod_info(project_id_to_update)
                if project_id_to_update in self.mod_list_item_map:
                    widget = self.mod_list_item_map[project_id_to_update]
                    widget.is_installed = False
                    widget.update_view()

        except OSError as e:
            self.log_to_console(f"Error deleting file {filename}: {e}")
        
        self.refresh_installed_mods()

    def handle_mod_toggle(self, filepath, is_enabled):
        new_path = None
        if is_enabled and filepath.endswith(".jar.disabled"):
            new_path = filepath[:-9]
        elif not is_enabled and filepath.endswith(".jar"):
            new_path = filepath + ".disabled"

        if new_path:
            try:
                os.rename(filepath, new_path)
                status = "enabled" if is_enabled else "disabled"
                self.log_to_console(f"Mod {os.path.basename(new_path)} has been {status}.")
                self.refresh_installed_mods()
            except Exception as e:
                self.log_to_console(f"Error toggling mod {os.path.basename(filepath)}: {e}")
                self.refresh_installed_mods()
        else:
            logging.warning(f"Mod toggle for {os.path.basename(filepath)} skipped: already in desired state.")

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
        if self.update_check_worker and self.update_check_worker.isRunning():
            return
        if manual:
            self.update_status_info["text"] = self.lang_dict.get("checking_updates", "Checking for updates...")
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
        self.version_status_label.setText(self.update_status_info.get("text", APP_VERSION))

    def show_update_dialog(self, event=None):
        if self.update_check_worker and self.update_check_worker.isRunning():
                 return
        fonts = {"main": self.minecraft_font, "subtitle": self.subtitle_font}
        dialog = UpdateDialog(self.latest_version_info, fonts, self.lang_dict, self)
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
        self.update_status_info = {"text": f"Update available: {version}", "is_update_available": True}
        self.update_version_display()
        if manual: self.show_update_dialog()

    def on_up_to_date(self, manual):
        self.latest_version_info = None
        self.update_status_info = {"text": self.lang_dict.get("latest_version", "You have the latest version"), "is_update_available": False}
        self.update_version_display()
        if manual: self.show_update_dialog()

    def on_update_error(self, error_text, manual):
        logging.error(f"Update error: {error_text}")
        self.latest_version_info = None
        self.update_status_info = {"text": self.lang_dict.get("error_checking_updates", "Error checking for updates"), "is_update_available": False}
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

        self.settings["jvm_args"] = self.settings.get("jvm_args", "")
        self.settings["java_path"] = self.settings.get("java_path", "")

        self.settings.update({
            "language": self.current_language,
            "memory": self.memory_slider.value(),
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "close_launcher": self.close_launcher_checkbox.isChecked(),
            "last_username": self.user_input.text(),
            "resolution_width": self.resolution_width_input.text(),
            "resolution_height": self.resolution_height_input.text(),
            "version_type": self.current_version_type,
            "last_version": self.version_combo.currentData(Qt.UserRole),
            "accent_color": self.current_accent_color,
            "last_tab": self.tab_widget.currentIndex()
        })
        
        settings.save_settings(self.settings)

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
        lang = self.lang_dict
        self.setWindowTitle(lang.get("app_title", "Hru Hru Launcher"))
        self.title_label.setText(lang["title"])
        self.version_label.setText(lang["version"])
        self.username_label.setText(lang["username"])
        self.launch_button.setText(lang["launch"])
        self.cancel_button.setText(lang.get("cancel", "Cancel"))
        self.user_input.setPlaceholderText(lang["enter_username"])
        
        self.tab_widget.setTabText(0, lang["news"])
        self.tab_widget.setTabText(1, lang["mods"])
        self.tab_widget.setTabText(2, lang.get("versions_management", "Versions"))
        self.tab_widget.setTabText(3, lang["modpacks"])
        self.tab_widget.setTabText(4, lang["vpn"])
        self.tab_widget.setTabText(5, "")
        self.tab_widget.setTabText(6, "")
        
        self.tab_widget.setTabToolTip(5, lang.get("tooltip_console", "Console"))
        self.tab_widget.setTabToolTip(6, lang.get("tooltip_settings", "Settings"))
        
        if hasattr(self, 'mods_sub_tabs'):
            self.mods_sub_tabs.setTabText(0, lang.get("search", "Search"))
            self.mods_sub_tabs.setTabText(1, lang.get("installed", "Installed"))
            self.refresh_installed_button.setText(lang.get("refresh", "Refresh"))
        
        if hasattr(self, 'refresh_versions_button'):
            self.refresh_versions_button.setText(lang.get("refresh", "Refresh"))
            self.refresh_versions_button.setToolTip(lang.get("refresh", "Refresh"))
            if hasattr(self, 'delete_selected_versions_button'):
                delete_tooltip = lang.get("delete_selected", "Delete Selected")
                self.delete_selected_versions_button.setText(delete_tooltip)
                self.delete_selected_versions_button.setToolTip(delete_tooltip)
            
        self.lang_label.setText(lang["language"])
        self.accent_color_label.setText(lang["accent_color"])
        self.color_picker_button.setText(lang["choose_color"])
        self.memory_label.setText(lang["memory"])
        self.fullscreen_checkbox.setText(lang["fullscreen"])
        self.close_launcher_checkbox.setText(lang["close_launcher"])
        self.clear_console_button.setText(lang["clear_console"])
        self.advanced_settings_button.setText(lang["advanced_settings_show"])
        self.resolution_label.setText(lang.get("resolution", "Game Resolution"))
        
        self.prev_page_button.setToolTip(lang.get("prev_page", "Previous"))
        self.next_page_button.setToolTip(lang.get("next_page", "Next"))
        self.page_label.setText(f"{lang.get('page', 'Page')} {self.mod_current_page}")
        self.version_type_label.setText(lang["version_type"])
        self.vanilla_radio.setText(lang["vanilla"])
        self.forge_radio.setText(lang["forge"])
        self.fabric_radio.setText(lang["fabric"])
        self.update_memory_feedback(self.memory_slider.value())
        if hasattr(self, 'open_mods_folder_button_search'):
            open_mods_folder_button_search.setToolTip(lang["open_mods_folder"])
        if hasattr(self, 'open_modpacks_folder_button'):
            self.open_modpacks_folder_button.setToolTip(lang["open_modpacks_folder"])
        self.modpacks_tab_label.setText(lang["wip_notice"])
        self.mod_search_input.setPlaceholderText(lang["search_mods_placeholder"])
        self.mod_sort_label.setText(lang["sort_by"])
        self.mod_refresh_button.setText(lang["refresh"])
        
        current_sort_data = self.mod_sort_combo.currentData()
        self.mod_sort_combo.clear()
        self.mod_sort_combo.addItem(lang["downloads"], "downloads")
        self.mod_sort_combo.addItem(lang["relevance"], "relevance")
        self.mod_sort_combo.addItem(lang["newest"], "newest")
        if current_sort_data:
            index = self.mod_sort_combo.findData(current_sort_data)
            if index != -1: self.mod_sort_combo.setCurrentIndex(index)
                
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, 'objectName') and tab.objectName() in ["news", "vpn"]:
                wip_label = tab.findChild(QLabel, "wipLabel")
                if wip_label: wip_label.setText(lang["wip_notice"])
            
    def apply_theme(self):
        base_style = themes.get_dark_theme(accent_color=self.current_accent_color)
        custom_style = """
            QPushButton { 
                outline: none; 
            }
            QTabBar::tab:nth-last-child(1), QTabBar::tab:nth-last-child(2) {
                width: 60px;
                padding: 10px 15px;
            }
            #totalSizeLabel {
                color: #bd93f9;
                font-size: 9pt;
            }
            #cancelButton {
                background-color: #ff5555;
            }
            #cancelButton:hover {
                background-color: #ff7070;
            }
            #deleteSelectedButton {
                background-color: #ff5555;
                padding: 5px 10px;
                border-radius: 5px;
            }
            #deleteSelectedButton:hover {
                background-color: #ff7070;
            }
            #deleteSelectedButton:disabled {
                background-color: #555;
                color: #888;
            }
        """
        self.setStyleSheet(base_style + custom_style)
        self.update_title_glow()

    def populate_versions(self, version_type="vanilla"):
        if self.version_loader and self.version_loader.isRunning():
            self.version_loader.quit()
            self.version_loader.wait()
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.version_combo.addItem(self.lang_dict["loading_versions"])
        
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
                        version_list = helpers.get_latest_versions(raw_versions)
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

    def on_tab_changed(self, index):
        current_widget = self.tab_widget.widget(index)
        if current_widget == self.mods_tab_widget:
            self.on_mods_sub_tab_changed(self.mods_sub_tabs.currentIndex())
        elif current_widget == self.versions_tab_widget:
            self.refresh_installed_versions_list()

    def on_mods_sub_tab_changed(self, index):
        if index == 0:
            if self.mod_results_list.count() == 0:
                self.mod_search_input.clear()
                self.update_mod_list()
        elif index == 1:
            self.refresh_installed_mods()

    def start_mod_download(self, mod_data):
        project_id = mod_data.get("project_id")
        if project_id in self.mod_download_workers and self.mod_download_workers[project_id].isRunning():
            return
        game_version_full = self.version_combo.currentData(Qt.UserRole)
        if not game_version_full:
            self.log_to_console("Error: no game version selected.")
            return
        game_version = game_version_full.split('-')[0]
        loader = self.current_version_type
        worker = ModDownloadWorker(project_id, game_version, loader, self.minecraft_directory, self.lang_dict, self)
        worker.progress.connect(self.on_mod_download_progress)
        worker.finished.connect(self.on_mod_download_finished)
        worker.mod_info_signal.connect(self.add_installed_mod_info)
        worker.finished.connect(worker.deleteLater)
        self.mod_download_workers[project_id] = worker
        worker.start()

    def install_mod_dependency(self, dependency_name):
        mods_tab_index = self.tab_widget.indexOf(self.mods_tab_widget)
        if mods_tab_index != -1:
            self.tab_widget.setCurrentIndex(mods_tab_index)
        self.mods_sub_tabs.setCurrentIndex(0)
        self.mod_search_input.setText(dependency_name)
        self.update_mod_list(reset_page=True)
        self.log_to_console(f"Automatically searching for dependency: {dependency_name}")
        
    def on_mod_download_progress(self, project_id, percentage):
        if project_id in self.mod_list_item_map:
            card_widget = self.mod_list_item_map[project_id]
            if percentage > 100:
                card_widget.update_view(is_installing=False)
            else:
                card_widget.update_view(is_installing=True, progress=percentage)

    def on_mod_download_finished(self, project_id, success, message):
        self.log_to_console(message)
        if project_id in self.mod_download_workers:
            del self.mod_download_workers[project_id]
        if project_id in self.mod_list_item_map:
            card_widget = self.mod_list_item_map[project_id]
            if success:
                card_widget.is_installed = True
            card_widget.update_view()

    def open_mod_page(self, mod_data):
        project_slug = mod_data.get("slug")
        if project_slug:
            url = QUrl(f"https://modrinth.com/mod/{project_slug}")
            QDesktopServices.openUrl(url)

    def get_installed_mods_info(self):
        try:
            if self.installed_mods_path and os.path.exists(self.installed_mods_path):
                with open(self.installed_mods_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.log_to_console(f"Error reading installed_mods.json: {e}")
        return {}

    def add_installed_mod_info(self, project_id, file_info):
        installed = self.get_installed_mods_info()
        installed[project_id] = file_info
        try:
            with open(self.installed_mods_path, 'w', encoding='utf-8') as f:
                json.dump(installed, f, indent=4)
        except IOError as e:
            self.log_to_console(f"Error saving the list of installed mods: {e}")

    def remove_installed_mod_info(self, project_id):
        installed = self.get_installed_mods_info()
        if project_id in installed:
            del installed[project_id]
            try:
                with open(self.installed_mods_path, 'w', encoding='utf-8') as f:
                    json.dump(installed, f, indent=4)
            except IOError as e:
                self.log_to_console(f"Error saving the list of installed mods: {e}")

    def delete_mod(self, mod_data):
        project_id = mod_data.get("project_id")
        installed_mods = self.get_installed_mods_info()
        if project_id in installed_mods:
            file_name = installed_mods[project_id].get("filename")
            if file_name:
                file_path = os.path.join(self.minecraft_directory, "mods", file_name)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        self.log_to_console(f"Error deleting file {file_name}: {e}")
            self.remove_installed_mod_info(project_id)
            if project_id in self.mod_list_item_map:
                card_widget = self.mod_list_item_map[project_id]
                card_widget.is_installed = False
                card_widget.update_view()

    def reinstall_version(self, version_id):
        version_path = os.path.join(self.minecraft_directory, "versions", version_id)
        self.log_to_console(f"Attempting to reinstall version {version_id}. Path: {version_path}")
        if os.path.exists(version_path):
            try:
                shutil.rmtree(version_path)
                self.log_to_console(f"Version folder '{version_id}' successfully deleted.")
                self.populate_versions(self.current_version_type)
            except Exception as e:
                self.log_to_console(f"Could not delete version folder: {e}")
                QMessageBox.critical(self, "Error", f"Could not delete folder '{version_path}'.\nCheck if the game is running or delete it manually.", QMessageBox.Ok)
        else:
            self.log_to_console(f"Version folder '{version_id}' not found for deletion.")
        
        if self.tab_widget.currentWidget() == self.versions_tab_widget:
            self.refresh_installed_versions_list()

    def log_to_console(self, message):
        self.console_output.append(message)
        logging.info(f"CONSOLE: {message}")

    def clear_console(self):
        self.console_output.clear()

    def update_memory_feedback(self, value):
        self.memory_value_label.setText(f"{value} GB")
        lang = self.lang_dict
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
        
    def on_version_sizes_scanned(self, sizes, total_size):
        total_size_str = helpers.format_size(total_size)
        total_label_text = self.lang_dict.get("total_versions_size", "Total size: {size}").format(size=total_size_str)
        self.total_versions_size_label.setText(total_label_text)
        
        grouped_sizes = {}
        for base_version, id_list in self.grouped_versions.items():
            group_size = sum(sizes.get(vid, 0) for vid in id_list)
            grouped_sizes[base_version] = group_size
        
        for base_version, widget in self.version_widget_map.items():
            size = grouped_sizes.get(base_version, 0)
            widget.update_size(size)

    def refresh_installed_versions_list(self):
        self.installed_versions_list.clear()
        self.grouped_versions.clear()
        self.version_widget_map.clear()
        self.selected_versions_for_deletion.clear()
        self.update_delete_button_state()
        self.total_versions_size_label.setText(self.lang_dict.get("calculating_size", "Calculating size..."))

        try:
            installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_directory)
            
            if not installed:
                item = QListWidgetItem(self.lang_dict.get("no_versions_installed", "No versions installed."))
                item.setTextAlignment(Qt.AlignCenter)
                self.installed_versions_list.addItem(item)
                self.total_versions_size_label.setText("")
                return

            all_version_ids = []
            for version_info in installed:
                version_id = version_info['id']
                all_version_ids.append(version_id)
                base_v = helpers.get_base_version(version_id)
                if base_v not in self.grouped_versions:
                    self.grouped_versions[base_v] = []
                self.grouped_versions[base_v].append(version_id)

            for base_version, id_list in sorted(self.grouped_versions.items(), key=lambda item: helpers.version_key(item[0]), reverse=True):
                version_types = sorted(list(set(helpers.get_version_type(vid) for vid in id_list)))
                
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 85))
                widget = VersionListItemWidget(base_version, version_types, self.version_management_icons, self.lang_dict)

                widget.delete_requested.connect(partial(self.handle_version_action, "delete", base_version))
                widget.repair_requested.connect(partial(self.handle_version_action, "repair", base_version))
                widget.open_folder_requested.connect(partial(self.handle_version_action, "open_folder", base_version))
                widget.selection_changed.connect(self.on_version_selection_changed)
                
                self.installed_versions_list.addItem(item)
                self.installed_versions_list.setItemWidget(item, widget)
                self.version_widget_map[base_version] = widget

            if self.version_size_scanner and self.version_size_scanner.isRunning():
                self.version_size_scanner.requestInterruption()
                self.version_size_scanner.wait()
            
            versions_path = os.path.join(self.minecraft_directory, "versions")
            self.version_size_scanner = VersionSizeScannerWorker(versions_path, all_version_ids, self)
            self.version_size_scanner.finished.connect(self.on_version_sizes_scanned)
            self.version_size_scanner.start()

        except Exception as e:
            self.log_to_console(f"Error scanning for installed versions: {e}")
            logging.error(f"Error scanning for installed versions: {traceback.format_exc()}")
            item = QListWidgetItem(self.lang_dict.get("error_scanning_versions", "Error during scan."))
            item.setTextAlignment(Qt.AlignCenter)
            self.installed_versions_list.addItem(item)
            self.total_versions_size_label.setText("")

    def handle_version_action(self, action_type, base_version):
        versions_in_group = self.grouped_versions.get(base_version, [])
        version_to_act_on = None

        if len(versions_in_group) == 1:
            version_to_act_on = versions_in_group[0]
        elif len(versions_in_group) > 1:
            title = self.lang_dict.get("select_version_dialog_title", "Select Version")
            prompt = self.lang_dict.get("select_version_prompt", "Select which version for '{base_version}' to {action}:").format(base_version=base_version, action=action_type)
            action_text = self.lang_dict.get(f"action_button_{action_type}", action_type.title())
            dialog = VersionSelectionDialog(title, prompt, versions_in_group, action_text, self.lang_dict, self)
            if dialog.exec() == QDialog.Accepted:
                version_to_act_on = dialog.get_selected_version()
        
        if not version_to_act_on:
            return

        if action_type in ["delete", "repair"]:
            confirm_title = self.lang_dict.get(f"confirm_{action_type}_title", f"Confirm {action_type.title()}")
            confirm_text = self.lang_dict.get(f"confirm_{action_type}_text", "Are you sure?").format(version_id=version_to_act_on)
            reply = QMessageBox.question(self, confirm_title, confirm_text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.reinstall_version(version_to_act_on)
        elif action_type == "open_folder":
            version_path = os.path.join(self.minecraft_directory, "versions", version_to_act_on)
            if os.path.exists(version_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(version_path))
            else:
                QMessageBox.warning(self, "Error", f"Folder for version '{version_to_act_on}' not found.")

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
        
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        
        worker_list = ['worker', 'version_loader', 'mod_search_worker',
                       'update_check_worker', 'local_mods_scanner', 'version_size_scanner']
        for worker_attr in worker_list:
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
        
    def on_version_selection_changed(self, base_version, is_selected):
        if is_selected:
            self.selected_versions_for_deletion.add(base_version)
        else:
            self.selected_versions_for_deletion.discard(base_version)
        
        self.update_delete_button_state()

    def update_delete_button_state(self):
        is_enabled = len(self.selected_versions_for_deletion) > 0
        if hasattr(self, 'delete_selected_versions_button'):
            self.delete_selected_versions_button.setEnabled(is_enabled)

    def delete_selected_versions(self):
        if not self.selected_versions_for_deletion:
            return

        versions_to_delete = []
        for base_version in self.selected_versions_for_deletion:
            versions_to_delete.extend(self.grouped_versions.get(base_version, []))
        
        if not versions_to_delete:
            return

        confirm_title = self.lang_dict.get("confirm_multi_delete_title", "Confirm Deletion")
        
        display_list = sorted(versions_to_delete)
        if len(display_list) > 10:
             display_list = display_list[:10] + ["..."]
        versions_list_str = "\n - ".join(display_list)

        confirm_text = self.lang_dict.get(
            "confirm_multi_delete_text", 
            "Are you sure you want to delete the following {count} versions?\n\n - {versions}"
        ).format(count=len(versions_to_delete), versions=versions_list_str)

        reply = QMessageBox.question(self, confirm_title, confirm_text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.log_to_console(f"Starting deletion of {len(versions_to_delete)} selected versions...")
            for version_id in versions_to_delete:
                self.reinstall_version(version_id) 
            
            self.log_to_console("Deletion complete.")
            self.refresh_installed_versions_list()