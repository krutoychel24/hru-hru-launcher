# hru_hru_launcher/ui/main_window.py

import sys
import os
import json
import subprocess
import traceback
import logging
from functools import partial
from PySide6.QtCore import (Qt, QThread, Signal, QPropertyAnimation, QEasingCurve, QSize, QPoint, QUrl)
from PySide6.QtGui import (QFont, QFontDatabase, QIcon, QPixmap, QColor, QStandardItemModel, QStandardItem, QDesktopServices)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
                                 QProgressBar, QFrame, QCheckBox, QSlider, QTabWidget, QTextEdit,
                                 QButtonGroup, QRadioButton, QGraphicsDropShadowEffect, QColorDialog, QListWidget, QListWidgetItem)
import minecraft_launcher_lib

from .widgets import AnimatedButton
from .widgets.mod_list_item import ModListItemWidget
from . import themes
from ..core.mc_worker import MinecraftWorker
from ..core import mod_manager
from ..utils.paths import get_assets_dir
from ..config import resources, settings


class ModSearchWorker(QThread):
    finished = Signal(list)
    def __init__(self, query, game_version, loader, sort_option, parent=None):
        super().__init__(parent)
        self.query = query
        self.game_version = game_version
        self.loader = loader
        self.sort_option = sort_option

    def run(self):
        logging.info(f"Начинаю поиск модов: query='{self.query}', version='{self.game_version}', loader='{self.loader}', sort='{self.sort_option}'")
        results = mod_manager.search_mods(self.query, self.game_version, self.loader, self.sort_option)
        logging.info(f"Поиск модов завершен, найдено {len(results)} результатов.")
        self.finished.emit(results)


class ModDownloadWorker(QThread):
    finished = Signal(str, bool, str)
    mod_info_signal = Signal(str, dict)
    progress = Signal(str, int)

    def __init__(self, project_id, game_version, loader, minecraft_dir, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.game_version = game_version
        self.loader = loader
        self.minecraft_dir = minecraft_dir
        self.is_running = True
        logging.info(f"[Worker {self.project_id}] Поток создан.")

    def run(self):
        try:
            logging.info(f"[Worker {self.project_id}] Поток запущен. Начинаю загрузку.")
            self.progress.emit(self.project_id, 0)

            logging.info(f"[Worker {self.project_id}] Получаю информацию о версии мода...")
            version_info = mod_manager.get_latest_mod_version(self.project_id, self.game_version, self.loader)
            if not version_info or not version_info.get("files"):
                logging.error(f"[Worker {self.project_id}] Не удалось найти совместимый файл.")
                self.finished.emit(self.project_id, False, f"Ошибка для {self.project_id}: не удалось найти совместимый файл.")
                return

            logging.info(f"[Worker {self.project_id}] Информация о версии получена. Ищу основной файл.")
            files = version_info.get("files", [])
            primary_file = next((f for f in files if f.get("primary")), files[0] if files else None)

            if not primary_file:
                logging.error(f"[Worker {self.project_id}] В манифесте версии не найдено файлов для скачивания.")
                self.finished.emit(self.project_id, False, f"Ошибка для {self.project_id}: не найдено файлов для скачивания.")
                return

            file_url = primary_file["url"]
            file_name = primary_file["filename"]
            mods_folder = os.path.join(self.minecraft_dir, "mods")
            logging.info(f"[Worker {self.project_id}] Начинаю скачивание файла '{file_name}' из '{file_url}'")

            def progress_handler(p):
                if self.is_running:
                    self.progress.emit(self.project_id, p)

            success = mod_manager.download_file(file_url, mods_folder, file_name, progress_handler)
            logging.info(f"[Worker {self.project_id}] Скачивание файла завершено со статусом: {success}")

            if success and self.is_running:
                file_info = {"filename": file_name, "url": file_url, "project_id": self.project_id}
                self.mod_info_signal.emit(self.project_id, file_info)
                self.finished.emit(self.project_id, True, f"Успешно скачан {file_name}")
            elif not self.is_running:
                self.finished.emit(self.project_id, False, f"Загрузка {file_name} отменена.")
            else:
                self.finished.emit(self.project_id, False, f"Не удалось скачать {file_name}.")

        except Exception as e:
            logging.critical(f"[Worker {self.project_id}] В потоке произошло необработанное исключение.", exc_info=True)
            self.finished.emit(self.project_id, False, f"Критическая ошибка в потоке: {e}")
        finally:
            if self.is_running:
                self.progress.emit(self.project_id, 101)
            logging.info(f"[Worker {self.project_id}] Поток завершает работу.")

    def stop(self):
        logging.info(f"[Worker {self.project_id}] Получена команда на остановку потока.")
        self.is_running = False


class MinecraftLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.version_loader = None
        self.mod_search_worker = None
        self.mod_download_workers = {}
        self.mod_list_item_map = {}

        self.settings = settings.load_settings()

        self.current_language = self.settings.get("language", "ru")
        self.current_accent_color = self.settings.get("accent_color", "#1DB954")
        self.current_version_type = self.settings.get("version_type", "vanilla")

        self.minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()
        os.makedirs(self.minecraft_directory, exist_ok=True)
        self.installed_mods_path = os.path.join(self.minecraft_directory, "installed_mods.json")

        self.init_fonts()
        self.init_icons()
        self.init_ui()

        self.tab_widget.currentChanged.connect(self.on_tab_changed)

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
            logging.warning("Шрифт не найден. Используется шрифт по умолчанию.")
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

        assets_dir = get_assets_dir()
        icon_path = os.path.join(assets_dir, "launcher-icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def init_ui(self):
        self.setWindowTitle("Hru Hru Launcher")
        self.setFixedSize(1280, 800)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.container = QWidget(self)
        self.container.setObjectName("container")
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.create_title_bar(main_layout)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(20, 10, 20, 20)
        self.create_main_panel(content_layout)
        self.create_tabs_panel(content_layout)
        main_layout.addLayout(content_layout)

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

        self.lang_label = QLabel()
        self.lang_label.setFont(self.subtitle_font)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Русский", "English"])
        self.language_combo.setCurrentIndex(0 if self.current_language == "ru" else 1)
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

        self.fullscreen_checkbox = QCheckBox()
        self.fullscreen_checkbox.setChecked(self.settings.get("fullscreen", False))
        self.close_launcher_checkbox = QCheckBox()
        self.close_launcher_checkbox.setChecked(self.settings.get("close_launcher", True))

        self.advanced_settings_button = QPushButton()
        self.advanced_settings_button.setCheckable(True)
        self.advanced_settings_button.toggled.connect(self.toggle_advanced_settings)

        self.advanced_settings_frame = QFrame()
        self.advanced_settings_frame.setObjectName("advancedFrame")
        self.advanced_settings_frame.setVisible(False)
        advanced_layout = QVBoxLayout(self.advanced_settings_frame)
        self.jvm_args_label = QLabel()
        self.jvm_args_label.setFont(self.subtitle_font)
        self.g1gc_checkbox = QCheckBox()
        self.g1gc_checkbox.setChecked(self.settings.get("use_g1gc", False))
        advanced_layout.addWidget(self.jvm_args_label)
        advanced_layout.addWidget(self.g1gc_checkbox)

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
        settings_layout.addWidget(self.fullscreen_checkbox)
        settings_layout.addWidget(self.close_launcher_checkbox)
        settings_layout.addStretch()
        settings_layout.addWidget(self.advanced_settings_button)
        settings_layout.addWidget(self.advanced_settings_frame)
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
        color = QColorDialog.getColor(initial_color, self, "Выберите акцентный цвет")
        if color.isValid():
            self.current_accent_color = color.name()
            self.update_color_preview()
            self.apply_theme()

    def update_color_preview(self):
        self.color_preview.setStyleSheet(f"background-color: {self.current_accent_color}; border: 2px solid #555555; border-radius: 8px;")

    def update_title_glow(self):
        self.glow_effect.setColor(QColor(self.current_accent_color))
        self.title_label.setGraphicsEffect(self.glow_effect)

    def save_settings(self):
        current_settings = {
            "language": self.current_language,
            "memory": self.memory_slider.value(),
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "close_launcher": self.close_launcher_checkbox.isChecked(),
            "last_username": self.user_input.text(),
            "use_g1gc": self.g1gc_checkbox.isChecked(),
            "version_type": self.current_version_type,
            "last_version": self.version_combo.currentData(Qt.UserRole),
            "accent_color": self.current_accent_color,
            "last_tab": self.tab_widget.currentIndex()
        }
        client_token = self.settings.get("clientToken")
        if client_token:
            current_settings["clientToken"] = client_token
        settings.save_settings(current_settings)

    def change_language(self, language_text):
        self.current_language = "ru" if language_text == "Русский" else "en"
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
        self.jvm_args_label.setText(lang["jvm_args"])
        self.g1gc_checkbox.setText(lang["use_g1gc"])
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
            if hasattr(tab, 'objectName') and tab.objectName() in ["news", "vpn"]:
                wip_label = tab.findChild(QLabel, "wipLabel")
                if wip_label:
                    wip_label.setText(lang["wip_notice"])
                    
    def apply_theme(self):
        self.setStyleSheet(themes.get_dark_theme(accent_color=self.current_accent_color))
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
        self.version_combo.addItem("Ошибка загрузки версий")
        self.error_label.setText(f"Не удалось загрузить список версий: {error_msg}")
        self.error_label.setVisible(True)
        self.log_to_console(f"Не удалось загрузить список версий: {error_msg}")

    def update_mod_list(self):
        query = self.mod_search_input.text()
        lang = resources.LANGUAGES[self.current_language]

        game_version_full = self.version_combo.currentData(Qt.UserRole)
        if not game_version_full:
            self.log_to_console("Для поиска модов выберите версию игры.")
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
            self.mod_search_worker.terminate()
        
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
        logging.info(f"Получен запрос на установку мода: project_id='{project_id}', title='{mod_data.get('title')}'")

        if project_id in self.mod_download_workers and self.mod_download_workers[project_id].isRunning():
            logging.warning(f"Загрузка для project_id='{project_id}' уже идет.")
            return

        self.log_to_console(f"Начинаю процесс загрузки для '{mod_data.get('title')}'...")
        logging.info(f"Начинаю процесс загрузки для '{mod_data.get('title')}'...")

        game_version_full = self.version_combo.currentData(Qt.UserRole)
        if not game_version_full:
            self.log_to_console("Ошибка: не выбрана версия игры.")
            logging.error("Не удалось начать загрузку: не выбрана версия игры.")
            return
            
        game_version = game_version_full.split('-')[0]
        loader = self.current_version_type
        logging.info(f"Параметры для загрузки: version='{game_version}', loader='{loader}'")

        worker = ModDownloadWorker(project_id, game_version, loader, self.minecraft_directory, self)
        
        worker.progress.connect(self.on_mod_download_progress)
        worker.finished.connect(self.on_mod_download_finished)
        worker.mod_info_signal.connect(self.add_installed_mod_info)
        worker.finished.connect(worker.deleteLater)

        self.mod_download_workers[project_id] = worker
        worker.start()
        logging.info(f"Поток для загрузки project_id='{project_id}' успешно запущен.")

    def on_mod_download_progress(self, project_id, percentage):
        if project_id in self.mod_list_item_map:
            card_widget = self.mod_list_item_map[project_id]
            if percentage > 100:
                card_widget.update_view(is_installing=False)
            else:
                card_widget.update_view(is_installing=True, progress=percentage)
        else:
            logging.warning(f"Получен прогресс для project_id='{project_id}', но виджет не найден в mod_list_item_map.")

    def on_mod_download_finished(self, project_id, success, message):
        logging.info(f"Получен сигнал finished для project_id='{project_id}', success={success}, message='{message}'")
        self.log_to_console(message)

        if project_id in self.mod_download_workers:
            del self.mod_download_workers[project_id]

        if project_id in self.mod_list_item_map:
            card_widget = self.mod_list_item_map[project_id]
            if success:
                card_widget.is_installed = True
            card_widget.update_view()
        else:
            logging.warning(f"Загрузка для project_id='{project_id}' завершена, но виджет не найден в mod_list_item_map.")

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
            self.log_to_console(f"Ошибка чтения installed_mods.json: {e}")
            logging.error("Ошибка чтения installed_mods.json", exc_info=True)
            return {}
        return {}

    def add_installed_mod_info(self, project_id, file_info):
        installed = self.get_installed_mods_info()
        installed[project_id] = file_info
        try:
            with open(self.installed_mods_path, 'w', encoding='utf-8') as f:
                json.dump(installed, f, indent=4)
            logging.info(f"Информация о моде {project_id} добавлена в installed_mods.json")
        except IOError:
            self.log_to_console(f"Ошибка сохранения списка установленных модов")
            logging.error(f"Ошибка записи в installed_mods.json", exc_info=True)

    def remove_installed_mod_info(self, project_id):
        installed = self.get_installed_mods_info()
        if project_id in installed:
            del installed[project_id]
            try:
                with open(self.installed_mods_path, 'w', encoding='utf-8') as f:
                    json.dump(installed, f, indent=4)
                logging.info(f"Информация о моде {project_id} удалена из installed_mods.json")
            except IOError:
                self.log_to_console(f"Ошибка сохранения списка установленных модов")
                logging.error(f"Ошибка записи в installed_mods.json", exc_info=True)

    def delete_mod(self, mod_data):
        project_id = mod_data.get("project_id")
        installed_mods = self.get_installed_mods_info()
        logging.info(f"Запрос на удаление мода {project_id}")

        if project_id in installed_mods:
            file_name = installed_mods[project_id].get("filename")
            if file_name:
                file_path = os.path.join(self.minecraft_directory, "mods", file_name)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        self.log_to_console(f"Удален файл мода: {file_name}")
                        logging.info(f"Удален файл мода: {file_path}")
                    except OSError:
                        self.log_to_console(f"Ошибка удаления файла {file_name}")
                        logging.error(f"Ошибка удаления файла {file_path}", exc_info=True)
                else:
                    self.log_to_console(f"Файл мода не найден, но запись удалена: {file_name}")
                    logging.warning(f"Файл мода {file_path} не найден для удаления, но запись будет удалена.")
            else:
                self.log_to_console(f"В записи для мода {mod_data.get('title')} нет имени файла.")
                logging.warning(f"В installed_mods.json для {project_id} отсутствует 'filename'.")
                
            self.remove_installed_mod_info(project_id)
            
            if project_id in self.mod_list_item_map:
                card_widget = self.mod_list_item_map[project_id]
                card_widget.is_installed = False
                card_widget.update_view()
        else:
            self.log_to_console(f"Мод {mod_data.get('title')} не найден в списке установленных.")
            logging.warning(f"Попытка удаления мода {project_id}, который не числится в installed_mods.json")

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

        jvm_args = {"use_g1gc": self.g1gc_checkbox.isChecked()}
        selected_version = self.version_combo.currentData(Qt.UserRole)
        mod_loader = self.current_version_type if self.current_version_type != "vanilla" else None

        self.worker = MinecraftWorker(
            mc_version=selected_version,
            username=username,
            minecraft_dir=self.minecraft_directory,
            client_token=self.settings.get("clientToken"),
            memory_gb=self.memory_slider.value(),
            fullscreen=self.fullscreen_checkbox.isChecked(),
            jvm_args=jvm_args,
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

    def on_launch_finished(self, result):
        lang = resources.LANGUAGES[self.current_language]
        self.launch_button.setEnabled(True)
        self.launch_button.setText(lang["launch"])
        self.progress_bar.setVisible(False)
        if result != "success":
            self.error_label.setText(result)
            self.error_label.setVisible(True)

        if self.close_launcher_checkbox.isChecked() and result == "success":
            self.close()

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

    def toggle_advanced_settings(self, checked):
        lang = resources.LANGUAGES[self.current_language]
        self.advanced_settings_frame.setVisible(checked)
        self.advanced_settings_button.setText(
            lang["advanced_settings_hide"] if checked else lang["advanced_settings_show"]
        )

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
        logging.info("Получена команда на остановку всех потоков.")
        for worker in list(self.mod_download_workers.values()):
            if worker.isRunning():
                worker.stop()
                worker.quit()
                worker.wait(500)
        self.mod_download_workers.clear()
        
        for worker_attr in ['worker', 'version_loader', 'mod_search_worker']:
            worker = getattr(self, worker_attr)
            if worker and worker.isRunning():
                worker.quit()
                worker.wait(500)
        logging.info("Все потоки остановлены.")

    def closeEvent(self, event):
        logging.info("Приложение закрывается. Сохранение настроек и остановка потоков...")
        self.save_settings()
        self.stop_all_threads()
        event.accept()

    def show(self):
        super().show()
        self.fade_in_animation.start()