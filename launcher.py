import sys
import os
import json
import subprocess
from pathlib import Path
import requests
import minecraft_launcher_lib
import uuid
from datetime import datetime, timezone
from PySide6.QtCore import (Qt, QThread, Signal, QPropertyAnimation, QEasingCurve,
                            QSize, QPoint, QStandardPaths)
from PySide6.QtGui import (QFont, QFontDatabase, QIcon, QPixmap, QColor)
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QComboBox, QLineEdit, QPushButton, QProgressBar,
                               QFrame, QCheckBox, QSlider, QTabWidget, QTextEdit,
                               QButtonGroup, QRadioButton, QGraphicsDropShadowEffect)

# Language settings
LANGUAGES = {
    "ru": {
        "title": "Hru Hru Launcher",
        "version": "Версия игры:",
        "username": "Имя пользователя:",
        "launch": "Запустить игру",
        "launching": "Запускается...",
        "loading_versions": "Загрузка версий...",
        "select_version": "Выберите версию",
        "enter_username": "Введите ваш ник",
        "enter_username_error": "Пожалуйста, введите имя пользователя!",
        "java_not_found": "Java не найдена. Пожалуйста, установите Java.",
        "error_occurred": "Произошла ошибка: ",
        "settings": "Настройки",
        "language": "Язык:",
        "theme": "Тема:",
        "dark_theme": "Тёмная",
        "light_theme": "Светлая",
        "neon_theme": "Неон",
        "memory": "Память (GB):",
        "fullscreen": "Полный экран",
        "close_launcher": "Закрыть лаунчер после запуска",
        "news": "Новости",
        "console": "Консоль",
        "clear_console": "Очистить консоль",
        "downloading": "Загрузка...",
        "installing": "Установка...",
        "starting": "Запуск игры...",
        "mem_feedback_risky": "Рискованно",
        "mem_feedback_low": "Минимум",
        "mem_feedback_optimal": "Оптимально",
        "mem_feedback_good": "Хорошо",
        "mem_feedback_excessive": "Избыточно",
        "advanced_settings_show": "Расширенные настройки",
        "advanced_settings_hide": "Скрыть настройки",
        "jvm_args": "Аргументы JVM:",
        "use_g1gc": "Использовать G1GC (улучшает производительность)",
        "version_type": "Тип версии:",
        "vanilla": "Vanilla",
        "forge": "Forge",
        "fabric": "Fabric"
    },
    "en": {
        "title": "Hru Hru Launcher",
        "version": "Minecraft Version:",
        "username": "Username:",
        "launch": "Launch Game",
        "launching": "Launching...",
        "loading_versions": "Loading versions...",
        "select_version": "Select version",
        "enter_username": "Enter your username",
        "enter_username_error": "Please enter a username!",
        "java_not_found": "Java not found. Please install Java.",
        "error_occurred": "An error occurred: ",
        "settings": "Settings",
        "language": "Language:",
        "theme": "Theme:",
        "dark_theme": "Dark",
        "light_theme": "Light",
        "neon_theme": "Neon",
        "memory": "Memory (GB):",
        "fullscreen": "Fullscreen",
        "close_launcher": "Close launcher after launch",
        "news": "News",
        "console": "Console",
        "clear_console": "Clear Console",
        "downloading": "Downloading...",
        "installing": "Installing...",
        "starting": "Starting game...",
        "mem_feedback_risky": "Risky",
        "mem_feedback_low": "Minimum",
        "mem_feedback_optimal": "Optimal",
        "mem_feedback_good": "Good",
        "mem_feedback_excessive": "Excessive",
        "advanced_settings_show": "Advanced Settings",
        "advanced_settings_hide": "Hide Settings",
        "jvm_args": "JVM Arguments:",
        "use_g1gc": "Use G1GC (improves performance)",
        "version_type": "Version Type:",
        "vanilla": "Vanilla",
        "forge": "Forge",
        "fabric": "Fabric"
    }
}

# SVG icons
PLAY_ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z"/></svg>'
SETTINGS_ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.82,11.69,4.82,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>'
GRASS_BLOCK_ICON_SVG = b'<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="grass_gradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#64be56"/><stop offset="100%" stop-color="#51a046"/></linearGradient><linearGradient id="dirt_gradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#8a5a37"/><stop offset="100%" stop-color="#70482d"/></linearGradient></defs><rect width="64" height="20" y="0" fill="url(#grass_gradient)" /><rect width="64" height="44" y="20" fill="url(#dirt_gradient)" /><rect width="64" height="2" y="18" fill="#458c3a" /></svg>'
NEWS_ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>'
CONSOLE_ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>'
VERSION_ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="white"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4c-1.1 0-2 .9-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58.55 0 1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41s-.22-1.05-.59-1.42zM13 20.01L4 11V4h7v-.01l9 9-7 7.01z"/><circle cx="6.5" cy="6.5" r="1.5"/></svg>'
USERNAME_ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="white"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'

def get_documents_path():
    """Returns the path to the user's Documents folder."""
    if sys.platform == "win32":
        import ctypes.wintypes
        CSIDL_PERSONAL = 5       # My Documents
        SHGFP_TYPE_CURRENT = 0   # Get current, not default value
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value
    elif sys.platform == "darwin": # macOS
        return os.path.expanduser("~/Documents")
    else: # Linux and other Unix-like systems
        return os.path.expanduser("~/Documents") # Common for many Linux distros

def get_launcher_data_dir():
    """Returns the path to the custom launcher data directory."""
    documents_path = get_documents_path()
    launcher_dir = os.path.join(documents_path, "Hru Hru Studio", "Hru Hru Launcher")
    os.makedirs(launcher_dir, exist_ok=True) # Create the directory if it doesn't exist
    return launcher_dir

# Functions for launcher_profiles.json management
def create_launcher_profiles_if_needed(minecraft_dir: str, client_token: str):
    profiles_path = os.path.join(minecraft_dir, "launcher_profiles.json")
    if not os.path.exists(profiles_path):
        base_structure = {
            "profiles": {},
            "settings": {
                "locale": "ru_ru",
                "enableSnapshots": True,
                "enableAdvanced": False
            },
            "version": 2,
            "clientToken": client_token
        }
        with open(profiles_path, "w", encoding="utf-8") as f:
            json.dump(base_structure, f, indent=4)
        print(f"'{profiles_path}' created.")

def add_profile(minecraft_dir: str, version_id: str, profile_name: str, icon: str = "Furnace"):
    profiles_path = os.path.join(minecraft_dir, "launcher_profiles.json")
    if not os.path.exists(profiles_path):
        print("Warning: launcher_profiles.json not found. Cannot add profile.")
        return

    with open(profiles_path, "r+", encoding="utf-8") as f:
        data = json.load(f)
        profile_id = uuid.uuid4().hex
        now_iso = datetime.now(timezone.utc).isoformat()

        new_profile = {
            "created": now_iso,
            "icon": icon,
            "lastUsed": now_iso,
            "lastVersionId": version_id,
            "name": profile_name,
            "type": "custom"
        }

        data["profiles"][profile_id] = new_profile
        data["selectedProfile"] = profile_id
        
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
        print(f"Profile '{profile_name}' added.")

# Helper classes for GUI
class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.original_geometry = None

    def enterEvent(self, event):
        if not self.original_geometry:
            self.original_geometry = self.geometry()
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.original_geometry.adjusted(-2, -2, 4, 4))
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.original_geometry:
            self.animation.stop()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.original_geometry)
            self.animation.start()
        super().leaveEvent(event)

import os
import uuid
import subprocess
from datetime import datetime
from PySide6.QtCore import QThread, Signal
import zipfile
import urllib.request


class MinecraftWorker(QThread):
    progress_update = Signal(int, int, str)
    finished = Signal(str)
    log_message = Signal(str)

    def __init__(self, mc_version, username, minecraft_dir, client_token, memory_gb=2, fullscreen=False, jvm_args=None, lang="ru", mod_loader=None):
        super().__init__()
        self.mc_version = mc_version
        self.username = username
        self.minecraft_dir = minecraft_dir
        self.client_token = client_token
        self.memory_gb = memory_gb
        self.fullscreen = fullscreen
        self.jvm_args = jvm_args if jvm_args else {}
        self.lang = lang
        self.mod_loader = mod_loader

    def _detect_forge_id(self, versions, base_mc_version):
        build = self.mc_version.split('-')[-1]
        for v in versions:
            vid = v['id'] if isinstance(v, dict) else v
            if 'forge' in vid and base_mc_version in vid and build in vid:
                return vid
        return None

    def run(self):
        callback = {
            "setStatus": lambda text: self.log_and_update_status(text),
            "setProgress": lambda value: self.progress_update.emit(value, 100, f"{LANGUAGES[self.lang]['downloading']} {value}%"),
            "setMax": lambda value: None
        }
        try:
            create_launcher_profiles_if_needed(self.minecraft_dir, self.client_token)
            base_mc_version = self.mc_version.split('-')[0] if self.mod_loader == 'forge' else self.mc_version
            self.log_and_update_status(f"Checking base version: {base_mc_version}")
            
            # This call uses minecraft_dir correctly, but library itself might use java.exe without flags
            minecraft_launcher_lib.install.install_minecraft_version(base_mc_version, self.minecraft_dir, callback=callback)
            
            base_version_path = os.path.join(self.minecraft_dir, "versions", base_mc_version)
            base_json_path = os.path.join(base_version_path, f"{base_mc_version}.json")
            if not os.path.isfile(base_json_path):
                raise Exception(f"Base version {base_mc_version} is not installed correctly (no {base_mc_version}.json).")
            
            version_id_to_launch = base_mc_version
            profile_name = base_mc_version

            if self.mod_loader in ['fabric', 'forge']:
                mods_path = os.path.join(self.minecraft_dir, "mods")
                if not os.path.exists(mods_path):
                    os.makedirs(mods_path)
                    self.log_and_update_status(f"Created 'mods' folder")

                if self.mod_loader == 'fabric':
                    self.log_and_update_status(f"Installing Fabric for {base_mc_version}")
                    minecraft_launcher_lib.fabric.install_fabric(base_mc_version, self.minecraft_dir, callback=callback)
                    installed_versions = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                    fabric_versions = [v for v in installed_versions if v["id"].startswith(f"fabric-loader-") and base_mc_version in v["id"]]
                    if not fabric_versions:
                        raise Exception(f"Fabric for Minecraft {base_mc_version} not found.")
                    version_id_to_launch = fabric_versions[0]["id"]
                    profile_name = f"{base_mc_version} Fabric"
                elif self.mod_loader == 'forge':
                    self.log_and_update_status(f"Installing Forge {self.mc_version}")
                    installed_versions = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                    version_id_to_launch = self._detect_forge_id(installed_versions, base_mc_version)

                    if version_id_to_launch:
                        profile_name = f"{base_mc_version} Forge"
                        self.log_and_update_status(f"Forge already installed: {version_id_to_launch}")
                    else:
                        versions_before = {v['id'] for v in installed_versions}
                        minecraft_launcher_lib.forge.install_forge_version(self.mc_version, self.minecraft_dir, callback=callback)
                        installed_versions = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                        versions_after = {v['id'] for v in installed_versions}
                        new_versions = versions_after - versions_before

                        if new_versions:
                            version_id_to_launch = new_versions.pop()
                            profile_name = f"{base_mc_version} Forge"
                            self.log_and_update_status(f"New Forge installed: {version_id_to_launch}")
                        else:
                            version_id_to_launch = self._detect_forge_id(installed_versions, base_mc_version)
                            if version_id_to_launch:
                                profile_name = f"{base_mc_version} Forge"
                                self.log_and_update_status(f"Forge found after installation: {version_id_to_launch}")
                            else:
                                raise Exception("Forge not installed and not found after installation.")

                        forge_version_dir = os.path.join(self.minecraft_dir, "versions", version_id_to_launch)
                        forge_json_path = os.path.join(forge_version_dir, f"{version_id_to_launch}.json")
                        if not os.path.isfile(forge_json_path):
                            self.log_and_update_status("Forge JSON not found. Attempting to extract from installer.jar...")
                            if not self.extract_forge_json_from_installer(forge_json_path):
                                self.log_and_update_status("Installer.jar not found locally. Downloading from Maven...")
                                if not self.download_and_extract_installer(self.mc_version, forge_json_path):
                                    self.log_and_update_status("Failed to extract Forge JSON. Generating manually...")
                                    self.generate_forge_json(base_json_path, forge_json_path, version_id_to_launch, base_mc_version)

            if self.mod_loader and (version_id_to_launch == base_mc_version):
                raise ValueError(f"Failed to find ID for {self.mod_loader} after installation.")
            elif not version_id_to_launch:
                raise ValueError("Failed to get final version ID for launch.")

            add_profile(self.minecraft_dir, version_id_to_launch, profile_name)

            all_jvm_args = [f"-Xmx{self.memory_gb}G", f"-Xms{self.memory_gb}G"]
            if self.jvm_args.get("use_g1gc", False):
                all_jvm_args.extend([
                    "-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=200",
                    "-XX:+UnlockExperimentalVMOptions", "-XX:+DisableExplicitGC", "-XX:+AlwaysPreTouch",
                    "-XX:G1NewSizePercent=30", "-XX:G1MaxNewSizePercent=40", "-XX:G1HeapRegionSize=8M",
                    "-XX:G1ReservePercent=20", "-XX:G1HeapWastePercent=5", "-XX:G1MixedGCCountTarget=4",
                    "-XX:InitiatingHeapOccupancyPercent=15", "-XX:G1MixedGCLiveThresholdPercent=90",
                    "-XX:G1RSetUpdatingPauseTimePercent=5", "-XX:SurvivorRatio=32", "-XX:+PerfDisableSharedMem",
                    "-XX:MaxTenuringThreshold=1"
                ])

            options = {
                "username": self.username,
                "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, self.username)),
                "token": "0",
                "jvmArguments": all_jvm_args,
                "fullscreen": self.fullscreen,
                "gameDirectory": get_launcher_data_dir() 
            }

            self.log_and_update_status(LANGUAGES[self.lang]['starting'])
            
            # Debug: print the minecraft_dir being used for clarity
            self.log_message.emit(f"Using Minecraft data directory: {self.minecraft_dir}")

            command = minecraft_launcher_lib.command.get_minecraft_command(version_id_to_launch, self.minecraft_dir, options)
            
            # --- NEW: Switch to javaw.exe for game launch ---
            # This part attempts to hide the console for the *game launch itself*.
            java_path = minecraft_launcher_lib.utils.get_java_executable()
            if sys.platform == "win32" and "java.exe" in java_path.lower():
                javaw_path = java_path.replace("java.exe", "javaw.exe")
                if os.path.exists(javaw_path):
                    command[0] = javaw_path
                    self.log_message.emit(f"Switched to javaw.exe for game launch: {javaw_path}")
                else:
                    self.log_message.emit(f"javaw.exe not found at {javaw_path}. Falling back to java.exe.")
            # --- END NEW BLOCK ---

            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.SW_HIDE | subprocess.CREATE_NO_WINDOW
            
            # --- CORRECTED SUBPROCESS.POPEN CALL ---
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creationflags,
                cwd=options.get('gameDirectory')
            )
            # --- END CORRECTED SUBPROCESS.POPEN CALL ---

            for line in iter(process.stdout.readline, ''):
                self.log_message.emit(line.strip())
            process.wait()
            self.finished.emit("success")
        except Exception as e:
            error_msg = f"{LANGUAGES[self.lang]['error_occurred']}{e}"
            self.log_message.emit(f"ERROR: {error_msg}")
            self.finished.emit(error_msg)

    def extract_forge_json_from_installer(self, forge_json_path):
        try:
            installer_path = self.find_installer_jar()
            if not installer_path:
                return False
            import zipfile # Ensure zipfile is imported inside the function or at top level
            with zipfile.ZipFile(installer_path, 'r') as jar:
                with jar.open('install_profile.json') as f:
                    install_profile = json.load(f)
                    forge_json_data = install_profile['versionInfo']
            os.makedirs(os.path.dirname(forge_json_path), exist_ok=True)
            with open(forge_json_path, "w", encoding="utf-8") as f:
                json.dump(forge_json_data, f, indent=4)
            self.log_and_update_status(f"Forge JSON successfully extracted: {forge_json_path}")
            return True
        except Exception as e:
            self.log_and_update_status(f"Failed to extract Forge JSON: {e}")
            return False

    def find_installer_jar(self):
        forge_lib_path = os.path.join(self.minecraft_dir, "libraries", "net", "minecraftforge", "forge", self.mc_version)
        for file in os.listdir(forge_lib_path) if os.path.exists(forge_lib_path) else []:
            if file.endswith("-installer.jar"):
                return os.path.join(forge_lib_path, file)
        return None

    def download_and_extract_installer(self, forge_version, forge_json_path):
        try:
            url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{forge_version}/forge-{forge_version}-installer.jar"
            installer_tmp = os.path.join(self.minecraft_dir, "tmp_installer.jar")
            import urllib.request # Ensure urllib.request is imported
            urllib.request.urlretrieve(url, installer_tmp)
            self.log_and_update_status(f"Downloaded installer.jar: {url}")
            result = self.extract_forge_json_from_installer(forge_json_path)
            os.remove(installer_tmp)
            return result
        except Exception as e:
            self.log_and_update_status(f"Failed to download installer.jar: {e}")
            return False

    def generate_forge_json(self, base_json_path, forge_json_path, version_id, base_version):
        try:
            with open(base_json_path, "r", encoding="utf-8") as f:
                base_json = json.load(f)
            base_json["id"] = version_id
            base_json["inheritsFrom"] = base_version
            base_json["mainClass"] = "net.minecraft.launchwrapper.Launch"
            base_json.setdefault("arguments", {})
            base_json["arguments"]["game"] = ["--tweakClass", "net.minecraftforge.fml.common.launcher.FMLTweaker"]
            os.makedirs(os.path.dirname(forge_json_path), exist_ok=True)
            with open(forge_json_path, "w", encoding="utf-8") as f:
                json.dump(base_json, f, indent=4)
            self.log_and_update_status(f"Forge JSON manually generated: {forge_json_path}")
        except Exception as e:
            raise Exception(f"Error generating Forge JSON: {e}")

    def log_and_update_status(self, text):
        self.progress_update.emit(0, 1, text)
        self.log_message.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

# Main Launcher Window
class MinecraftLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.version_loader = None
        self.settings_file_path = os.path.join(get_launcher_data_dir(), "launcher_settings.json")
        self.settings = self.load_settings()
        self.current_language = self.settings.get("language", "ru")
        self.current_theme = self.settings.get("theme", "dark")
        self.current_version_type = self.settings.get("version_type", "vanilla")
        self.init_fonts()
        self.init_icons()
        self.init_ui()
        self.minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()
        self.old_pos = None
        self.setWindowOpacity(0)
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)

    def init_fonts(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        font_path = os.path.join(script_dir, "Minecraftia.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            self.minecraft_font = QFont(font_families[0], 10)
            self.title_font = QFont(font_families[0], 28, QFont.Bold)
            self.subtitle_font = QFont(font_families[0], 14)
        else:
            print(f"WARNING: Font 'Minecraftia.ttf' not found in '{script_dir}'. Using default font.")
            self.minecraft_font = QFont("Arial", 10)
            self.title_font = QFont("Arial", 24, QFont.Bold)
            self.subtitle_font = QFont("Arial", 12)

    def init_icons(self):
        def create_icon(svg_data):
            pixmap = QPixmap()
            pixmap.loadFromData(svg_data)
            return QIcon(pixmap)
        self.play_icon = create_icon(PLAY_ICON_SVG)
        self.settings_icon = create_icon(SETTINGS_ICON_SVG)
        self.news_icon = create_icon(NEWS_ICON_SVG)
        self.console_icon = create_icon(CONSOLE_ICON_SVG)
        self.version_icon = create_icon(VERSION_ICON_SVG)
        self.username_icon = create_icon(USERNAME_ICON_SVG)
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "launcher-icon.ico")
        else:
            icon_path = "launcher-icon.ico"

        self.setWindowIcon(QIcon(icon_path))

    def init_ui(self):
        self.setWindowTitle("Hru Hru Launcher")
        self.setFixedSize(900, 650)
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
        
    def create_title_bar(self, main_layout):
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(60)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 10, 20, 10)

        self.title_label = QLabel()
        self.title_label.setFont(self.title_font)
        self.title_label.setObjectName("titleLabel")
        glow_effect = QGraphicsDropShadowEffect(self)
        glow_effect.setColor(QColor(64, 158, 255))
        glow_effect.setBlurRadius(25)
        glow_effect.setOffset(0,0)
        self.title_label.setGraphicsEffect(glow_effect)
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
        main_layout.addWidget(title_bar)

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
        
        if self.current_version_type not in version_type_map:
            self.current_version_type = "vanilla"
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
        panel_layout.addSpacing(10)
        panel_layout.addLayout(version_layout)
        panel_layout.addWidget(self.version_combo)
        panel_layout.addSpacing(10)
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

        self.create_settings_tab()
        self.create_news_tab()
        self.create_console_tab()
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

        self.theme_label = QLabel()
        self.theme_label.setFont(self.subtitle_font)
        self.theme_group = QButtonGroup()
        self.dark_theme_radio = QRadioButton()
        self.light_theme_radio = QRadioButton()
        self.neon_theme_radio = QRadioButton()
        self.theme_group.addButton(self.dark_theme_radio, 0)
        self.theme_group.addButton(self.light_theme_radio, 1)
        self.theme_group.addButton(self.neon_theme_radio, 2)
        
        theme_map = {"dark": 0, "light": 1, "neon": 2}
        self.theme_group.button(theme_map.get(self.current_theme, 0)).setChecked(True)
        self.theme_group.idClicked.connect(self.change_theme)

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
        self.advanced_settings_button.setObjectName("advancedButton")

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
        settings_layout.addWidget(self.theme_label)
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(self.dark_theme_radio)
        theme_layout.addWidget(self.light_theme_radio)
        theme_layout.addWidget(self.neon_theme_radio)
        theme_layout.addStretch()
        settings_layout.addLayout(theme_layout)
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

    def create_news_tab(self):
        news_widget = QWidget()
        news_layout = QVBoxLayout(news_widget)
        news_label = QLabel("Minecraft news will appear here!")
        news_label.setAlignment(Qt.AlignCenter)
        news_layout.addWidget(news_label)
        self.tab_widget.addTab(news_widget, self.news_icon, "")

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

    def load_settings(self):
        defaults = {
            "language": "ru", "theme": "dark", "memory": 4, "fullscreen": False, 
            "close_launcher": True, "last_username": "", "use_g1gc": False, 
            "version_type": "vanilla", "last_version": ""
        }
        if os.path.exists(self.settings_file_path): 
            try:
                with open(self.settings_file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                defaults.update(settings)
            except (json.JSONDecodeError, IOError):
                print(f"Error loading settings from {self.settings_file_path}. Using default settings. Error: {e}")
                pass
        if "clientToken" not in defaults:
            defaults["clientToken"] = uuid.uuid4().hex
        return defaults

    def save_settings(self):
        self.settings["clientToken"] = self.settings.get("clientToken", uuid.uuid4().hex)
        settings = {
            "language": self.current_language,
            "theme": self.current_theme,
            "memory": self.memory_slider.value(),
            "fullscreen": self.fullscreen_checkbox.isChecked(),
            "close_launcher": self.close_launcher_checkbox.isChecked(),
            "last_username": self.user_input.text(),
            "use_g1gc": self.g1gc_checkbox.isChecked(),
            "version_type": self.current_version_type,
            "last_version": self.version_combo.currentText(),
            "clientToken": self.settings["clientToken"]
        }
        with open(self.settings_file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    def change_language(self, language_text):
        self.current_language = "ru" if language_text == "Русский" else "en"
        self.update_ui_text()

    def change_theme(self, theme_id):
        themes = {0: "dark", 1: "light", 2: "neon"}
        self.current_theme = themes.get(theme_id, "dark")
        self.apply_theme()

    def change_version_type(self, type_id):
        types = {0: "vanilla", 1: "forge", 2: "fabric"}
        self.current_version_type = types.get(type_id, "vanilla")
        self.populate_versions(self.current_version_type)

    def update_ui_text(self):
        lang = LANGUAGES[self.current_language]
        self.title_label.setText(lang["title"])
        self.version_label.setText(lang["version"])
        self.username_label.setText(lang["username"])
        self.launch_button.setText(lang["launch"])
        self.version_combo.setPlaceholderText(lang["loading_versions"])
        self.user_input.setPlaceholderText(lang["enter_username"])
        self.tab_widget.setTabText(0, lang["settings"])
        self.tab_widget.setTabText(1, lang["news"])
        self.tab_widget.setTabText(2, lang["console"])
        self.lang_label.setText(lang["language"])
        self.theme_label.setText(lang["theme"])
        self.dark_theme_radio.setText(lang["dark_theme"])
        self.light_theme_radio.setText(lang["light_theme"])
        self.neon_theme_radio.setText(lang["neon_theme"])
        self.memory_label.setText(lang["memory"])
        self.fullscreen_checkbox.setText(lang["fullscreen"])
        self.close_launcher_checkbox.setText(lang["close_launcher"])
        self.clear_console_button.setText(lang["clear_console"])
        self.advanced_settings_button.setText(lang["advanced_settings_show"])
        self.jvm_args_label.setText(lang["jvm_args"])
        self.g1gc_checkbox.setText(lang["use_g1gc"])
        self.update_memory_feedback(self.memory_slider.value())
        self.version_type_label.setText(lang["version_type"])
        self.vanilla_radio.setText(lang["vanilla"])
        self.forge_radio.setText(lang["forge"])
        self.fabric_radio.setText(lang["fabric"])

    def apply_theme(self):
        themes = {"dark": self.get_dark_theme(), "light": self.get_light_theme(), "neon": self.get_neon_theme()}
        self.setStyleSheet(themes.get(self.current_theme, self.get_dark_theme()))

    def get_dark_theme(self):
        return """
            #container {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(20, 25, 35, 255), stop:1 rgba(35, 40, 55, 255));
                border-radius: 15px; border: 1px solid rgba(64, 158, 255, 0.3);
            }
            #titleBar {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(25, 30, 40, 255), stop:1 rgba(40, 45, 60, 255));
                border-radius: 15px 15px 0 0; border-bottom: 1px solid rgba(64, 158, 255, 0.3);
            }
            #titleLabel { color: #ffffff; font-weight: bold; }
            #mainPanel {
                background: rgba(25, 30, 40, 0.7); border-radius: 10px;
                border: 1px solid rgba(64, 158, 255, 0.2);
            }
            #sectionLabel { color: #64beff; font-weight: bold; }
            QLabel, QRadioButton, QCheckBox { color: #c0c8d1; }
            QComboBox, QLineEdit {
                background: rgba(35, 40, 55, 0.8); border: 2px solid rgba(64, 158, 255, 0.3);
                border-radius: 8px; padding: 10px; color: #ffffff;
            }
            QComboBox:hover, QLineEdit:hover { border: 2px solid rgba(64, 158, 255, 0.6); }
            QLineEdit:focus { border: 2px solid #64beff; }
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(100, 190, 255, 255), stop:1 rgba(64, 158, 255, 255));
                color: white; border: none; border-radius: 8px; padding: 12px; font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(120, 210, 255, 255), stop:1 rgba(84, 178, 255, 255));
            }
            #closeButton, #minimizeButton { font-size: 12pt; font-weight: bold; border-radius: 15px; }
            #closeButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #ff7878, stop:1 #ff5050); color: white;}
            #minimizeButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #ffc864, stop:1 #ffb43c); color: white;}
            QProgressBar {
                border: 2px solid rgba(64, 158, 255, 0.3); border-radius: 8px; text-align: center;
                background: rgba(35, 40, 55, 0.8); color: white; font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #409eff, stop:1 #64beff);
                border-radius: 6px;
            }
            #errorLabel { color: #ff6b6b; font-weight: bold; }
            QTabWidget::pane {
                border: 2px solid rgba(64, 158, 255, 0.3); border-radius: 8px;
                background: rgba(25, 30, 40, 0.7);
            }
            QTabBar::tab {
                background: rgba(35, 40, 55, 0.8); color: #c0c8d1; padding: 10px 15px;
                margin-right: 2px; border-radius: 5px 5px 0 0; border: 1px solid rgba(64, 158, 255, 0.3);
            }
            QTabBar::tab:selected { background: rgba(64, 158, 255, 0.3); color: #ffffff; border-bottom: 2px solid #64beff; }
            QTabBar::tab:hover { background: rgba(64, 158, 255, 0.2); }
            QCheckBox, QRadioButton { spacing: 8px; }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 18px; height: 18px; border: 2px solid rgba(64, 158, 255, 0.3);
                background: rgba(35, 40, 55, 0.8);
            }
            QCheckBox::indicator { border-radius: 3px; }
            QRadioButton::indicator { border-radius: 9px; }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: #64beff; border: 2px solid #64beff; }
            QSlider::groove:horizontal {
                border: 1px solid rgba(64, 158, 255, 0.3); height: 8px;
                background: rgba(35, 40, 55, 0.8); border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #64beff; border: 2px solid #64beff; width: 20px;
                margin: -6px 0; border-radius: 10px;
            }
            QTextEdit {
                background: rgba(20, 25, 35, 0.9); border: 1px solid rgba(64, 158, 255, 0.3);
                border-radius: 8px; color: #c0c8d1; padding: 10px;
            }
            #advancedButton { background: #4a5568; }
            #advancedButton:checked { background: #2d3748; }
            #advancedFrame {
                background: rgba(20, 25, 30, 0.5);
                border: 1px solid rgba(64, 158, 255, 0.1);
                border-radius: 5px;
            }
        """

    def get_light_theme(self):
        return """
            #container {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f0f5fa, stop:1 #dce6f0);
                border-radius: 15px; border: 1px solid rgba(100, 150, 200, 0.5);
            }
            #titleBar {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #e6f0fa, stop:1 #d2e1f0);
                border-radius: 15px 15px 0 0; border-bottom: 1px solid rgba(100, 150, 200, 0.5);
            }
            #titleLabel { color: #1a365d; font-weight: bold; }
            #mainPanel {
                background: rgba(250, 255, 255, 0.8); border-radius: 10px;
                border: 1px solid rgba(100, 150, 200, 0.3);
            }
            #sectionLabel { color: #2b6cb0; font-weight: bold; }
            QLabel, QRadioButton, QCheckBox { color: #2d3748; }
            QComboBox, QLineEdit {
                background: rgba(255, 255, 255, 0.9); border: 2px solid rgba(100, 150, 200, 0.4);
                border-radius: 8px; padding: 10px; color: #2d3748;
            }
            QComboBox:hover, QLineEdit:hover { border: 2px solid rgba(100, 150, 200, 0.7); }
            QLineEdit:focus { border: 2px solid #2b6cb0; }
            QPushButton {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #38b2ac, stop:1 #2b6cb0);
                color: white; border: none; border-radius: 8px; padding: 12px; font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4fd1c5, stop:1 #3182ce);
            }
            #closeButton, #minimizeButton { font-size: 12pt; font-weight: bold; border-radius: 15px; color: white;}
            #closeButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #f56565, stop:1 #e53e3e); }
            #minimizeButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #f6ad55, stop:1 #ed8936); }
            QProgressBar {
                border: 2px solid rgba(100, 150, 200, 0.4); border-radius: 8px; text-align: center;
                background: rgba(255, 255, 255, 0.9); color: #2d3748; font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2b6cb0, stop:1 #38b2ac);
                border-radius: 6px;
            }
            #errorLabel { color: #e53e3e; font-weight: bold; }
            QTabWidget::pane {
                border: 2px solid rgba(100, 150, 200, 0.4); border-radius: 8px;
                background: rgba(250, 255, 255, 0.8);
            }
            QTabBar::tab {
                background: rgba(255, 255, 255, 0.9); color: #2d3748; padding: 10px 15px;
                margin-right: 2px; border-radius: 5px 5px 0 0; border: 1px solid rgba(100, 150, 200, 0.4);
            }
            QTabBar::tab:selected { background: rgba(100, 150, 200, 0.3); color: #1a365d; border-bottom: 2px solid #2b6cb0; }
            QTabBar::tab:hover { background: rgba(100, 150, 200, 0.2); }
            QTextEdit {
                background: #e2e8f0; border: 1px solid #cbd5e0;
                border-radius: 8px; color: #2d3748; padding: 10px;
            }
        """

    def get_neon_theme(self):
        return """
            #container {
                background: #0d0d0d;
                border-radius: 15px; border: 1px solid #00ffff;
            }
            #titleBar {
                background: #1a1a1a;
                border-radius: 15px 15px 0 0; border-bottom: 1px solid #00ffff;
            }
            #titleLabel { color: #00ffff; font-weight: bold; }
            #mainPanel { background: #1a1a1a; border-radius: 10px; border: 1px solid #00ffff; }
            #sectionLabel { color: #ff00ff; font-weight: bold; }
            QLabel, QRadioButton, QCheckBox { color: #e0e0e0; }
            QComboBox, QLineEdit {
                background: #1a1a1a; border: 2px solid #00ffff;
                border-radius: 8px; padding: 10px; color: #e0e0e0;
            }
            QComboBox:hover, QLineEdit:hover { border: 2px solid #ff00ff; }
            QPushButton {
                background: #00ffff; color: #0d0d0d; border: none;
                border-radius: 8px; padding: 12px; font-weight: bold;
            }
            QPushButton:hover { background: #ff00ff; }
            #closeButton { background: #ff00ff; border-radius: 15px; color: black; }
            #minimizeButton { background: #00ffff; border-radius: 15px; color: black; }
            QProgressBar {
                border: 2px solid #00ffff; border-radius: 8px; text-align: center;
                background: #1a1a1a; color: #e0e0e0; font-weight: bold;
            }
            QProgressBar::chunk { background: #ff00ff; border-radius: 6px; }
            #errorLabel { color: #ff00ff; font-weight: bold; }
            QTabWidget::pane { border: 2px solid #00ffff; border-radius: 8px; background: #1a1a1a; }
            QTabBar::tab { background: #1a1a1a; color: #e0e0e0; padding: 10px 15px; border: 1px solid #00ffff; }
            QTabBar::tab:selected { background: #ff00ff; color: #0d0d0d; }
            QTextEdit { background: #0d0d0d; border: 1px solid #00ffff; color: #e0e0e0; }
        """

    def populate_versions(self, version_type="vanilla"):
        self.version_combo.clear()
        self.version_combo.setEnabled(False)
        self.version_combo.setPlaceholderText(LANGUAGES[self.current_language]["loading_versions"])
        
        class VersionLoader(QThread):
            finished = Signal(list)
            error = Signal(str)
            def __init__(self, v_type):
                super().__init__()
                self.v_type = v_type
            
            def run(self):
                version_list = []
                try:
                    if self.v_type == "vanilla":
                        version_list = [v['id'] for v in minecraft_launcher_lib.utils.get_version_list() if v['type'] == 'release']
                    elif self.v_type == "forge":
                        version_list = minecraft_launcher_lib.forge.list_forge_versions()
                    elif self.v_type == "fabric":
                        version_list = minecraft_launcher_lib.fabric.get_stable_minecraft_versions()
                    self.finished.emit(version_list)
                except Exception as e:
                    print(f"Error loading {self.v_type} versions: {e}")
                    self.error.emit(str(e))

        self.version_loader = VersionLoader(version_type)
        self.version_loader.finished.connect(self.on_versions_loaded)
        self.version_loader.error.connect(self.on_version_load_error)
        self.version_loader.start()

    def on_versions_loaded(self, version_list):
        self.version_combo.clear()
        self.version_combo.addItems(version_list)
        last_version = self.settings.get("last_version")
        if last_version and self.version_combo.findText(last_version) != -1:
            self.version_combo.setCurrentText(last_version)
        self.version_combo.setEnabled(True)
        self.version_combo.setPlaceholderText(LANGUAGES[self.current_language]["select_version"])
    
    def on_version_load_error(self, error_msg):
        self.version_combo.setPlaceholderText("Error loading versions")
        self.error_label.setText(f"Failed to load version list: {error_msg}")
        self.error_label.setVisible(True)

    def start_minecraft(self):
        if self.worker and self.worker.isRunning():
            return

        username = self.user_input.text()
        if not username:
            self.error_label.setText(LANGUAGES[self.current_language]["enter_username_error"])
            self.error_label.setVisible(True)
            return

        self.launch_button.setEnabled(False)
        self.launch_button.setText(LANGUAGES[self.current_language]["launching"])
        self.progress_bar.setVisible(True)
        self.error_label.setVisible(False)
        self.tab_widget.setCurrentIndex(2) # Switch to console tab

        jvm_args = {
            "use_g1gc": self.g1gc_checkbox.isChecked()
        }

        selected_version = self.version_combo.currentText()
        mod_loader = self.current_version_type if self.current_version_type != "vanilla" else None

        self.worker = MinecraftWorker(
            mc_version=selected_version,
            username=username,
            minecraft_dir=self.minecraft_directory,
            client_token=self.settings["clientToken"],
            memory_gb=self.memory_slider.value(),
            fullscreen=self.fullscreen_checkbox.isChecked(),
            jvm_args=jvm_args,
            lang=self.current_language,
            mod_loader=mod_loader 
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
        self.launch_button.setEnabled(True)
        self.launch_button.setText(LANGUAGES[self.current_language]["launch"])
        self.progress_bar.setVisible(False)
        if result != "success":
            self.error_label.setText(result)
            self.error_label.setVisible(True)

        if self.close_launcher_checkbox.isChecked() and result == "success":
            self.close()

    def log_to_console(self, message):
        self.console_output.append(message)

    def clear_console(self):
        self.console_output.clear()

    def update_memory_feedback(self, value):
        self.memory_value_label.setText(f"{value} GB")
        lang = LANGUAGES[self.current_language]

        if value <= 1:
            text, color = lang["mem_feedback_risky"], "#ff6b6b"
        elif value <= 3:
            text, color = lang["mem_feedback_low"], "#f9a825"
        elif value <= 6:
            text, color = lang["mem_feedback_optimal"], "#7cb342"
        elif value <= 8:
            text, color = lang["mem_feedback_good"], "#43a047"
        else:
            text, color = lang["mem_feedback_excessive"], "#fdd835"

        self.memory_feedback_label.setText(text)
        self.memory_feedback_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    def toggle_advanced_settings(self, checked):
        lang = LANGUAGES[self.current_language]
        self.advanced_settings_frame.setVisible(checked)
        self.advanced_settings_button.setText(lang["advanced_settings_hide"] if checked else lang["advanced_settings_show"])

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def closeEvent(self, event):
        self.save_settings()
        if self.version_loader and self.version_loader.isRunning():
            self.version_loader.terminate()
            self.version_loader.wait()
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

    def show(self):
        super().show()
        self.fade_in_animation.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = MinecraftLauncher()
    launcher.show()
    sys.exit(app.exec())