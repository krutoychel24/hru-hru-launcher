import os
import sys
import uuid
import subprocess
from datetime import datetime

from PySide6.QtCore import QThread, Signal
import minecraft_launcher_lib

from .profile_manager import create_launcher_profiles_if_needed, add_profile
from ..config import resources, settings

class GameProcessError(Exception):
    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code


class MinecraftWorker(QThread):
    progress_update = Signal(int, int, str)
    finished = Signal(str, object)
    log_message = Signal(str)

    def __init__(
        self,
        mc_version,
        username,
        minecraft_dir,
        client_token,
        memory_gb=2,
        fullscreen=False,
        options=None,
        lang="ru",
        mod_loader=None
    ):
        super().__init__()
        self.mc_version = mc_version
        self.username = username
        self.minecraft_dir = minecraft_dir
        self.client_token = client_token
        self.memory_gb = memory_gb
        self.fullscreen = fullscreen
        self.options = options if options else {}
        self.lang = lang
        self.mod_loader = mod_loader

    def _detect_forge_id(self, versions, base_mc_version):
        build = self.mc_version.split("-")[-1]
        for v in versions:
            vid = v["id"] if isinstance(v, dict) else v
            if "forge" in vid and base_mc_version in vid and build in vid:
                return vid
        return None

    def run(self):
        callback = {
            "setStatus": lambda text: self.log_and_update_status(text),
            "setProgress": lambda value: self.progress_update.emit(
                value, 100, f"{resources.LANGUAGES[self.lang]['downloading']} {value}%"
            ),
            "setMax": lambda value: None,
        }
        
        version_id_to_launch = ""
        command = []

        try:
            create_launcher_profiles_if_needed(self.minecraft_dir, self.client_token)
            
            base_mc_version = (
                self.mc_version.split("-")[0]
                if self.mod_loader == "forge"
                else self.mc_version
            )

            installed_version_ids = [v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)]
            if base_mc_version not in installed_version_ids:
                self.log_and_update_status(f"Base version {base_mc_version} not found. Installing...")
                minecraft_launcher_lib.install.install_minecraft_version(
                    base_mc_version, self.minecraft_dir, callback=callback
                )
            else:
                self.log_and_update_status(f"Base version {base_mc_version} already installed.")

            version_id_to_launch = base_mc_version
            profile_name = base_mc_version

            if self.mod_loader in ["fabric", "forge"]:
                mods_path = os.path.join(self.minecraft_dir, "mods")
                if not os.path.exists(mods_path):
                    os.makedirs(mods_path)
                    self.log_and_update_status(f"Created 'mods' folder")

                if self.mod_loader == "fabric":
                    installed_versions_data = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                    fabric_versions = [v for v in installed_versions_data if v["id"].startswith(f"fabric-loader-") and base_mc_version in v["id"]]
                    
                    if not fabric_versions:
                        self.log_and_update_status(f"Installing Fabric for {base_mc_version}")
                        minecraft_launcher_lib.fabric.install_fabric(
                            base_mc_version, self.minecraft_dir, callback=callback
                        )
                        installed_versions_data_after = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                        fabric_versions = [v for v in installed_versions_data_after if v["id"].startswith(f"fabric-loader-") and base_mc_version in v["id"]]
                        if not fabric_versions:
                            raise Exception(f"Fabric for Minecraft {base_mc_version} not found after installation.")
                        self.log_and_update_status(f"Fabric installed: {fabric_versions[0]['id']}")
                    else:
                        self.log_and_update_status(f"Found existing Fabric version: {fabric_versions[0]['id']}")
                    
                    version_id_to_launch = fabric_versions[0]["id"]
                    profile_name = f"{base_mc_version} Fabric"
                
                elif self.mod_loader == "forge":
                    all_installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                    version_id_to_launch = self._detect_forge_id(all_installed, base_mc_version)

                    if not version_id_to_launch:
                        self.log_and_update_status(f"Installing Forge {self.mc_version}")
                        try:
                            minecraft_launcher_lib.forge.install_forge_version(
                                self.mc_version, self.minecraft_dir, callback=callback
                            )
                        except Exception as forge_install_error:
                            self.log_message.emit(f"Forge installation failed: {forge_install_error}.")
                            raise forge_install_error
                        
                        all_installed_after = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                        version_id_to_launch = self._detect_forge_id(all_installed_after, base_mc_version)
                        if not version_id_to_launch:
                            raise Exception(f"Could not find Forge version for {self.mc_version} after installation.")
                        self.log_and_update_status(f"New Forge version installed: {version_id_to_launch}")
                    else:
                        self.log_and_update_status(f"Found existing Forge version: {version_id_to_launch}")
                    
                    profile_name = f"{base_mc_version} Forge"
            
            add_profile(self.minecraft_dir, version_id_to_launch, profile_name)

            custom_jvm_args = self.options.get("jvmArguments", [])
            all_jvm_args = [f"-Xmx{self.memory_gb}G", f"-Xms{self.memory_gb}G"] + custom_jvm_args
            
            launch_options = {
                "username": self.username,
                "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, self.username)),
                "token": "0",
                "jvmArguments": all_jvm_args,
                "fullscreen": self.fullscreen,
                "gameDirectory": self.minecraft_dir,
                "executablePath": self.options.get("executablePath"),
                "resolutionWidth": self.options.get("resolutionWidth"),
                "resolutionHeight": self.options.get("resolutionHeight"),
            }
            
            launch_options = {k: v for k, v in launch_options.items() if v}

            self.log_and_update_status(resources.LANGUAGES[self.lang]["starting"])
            self.log_message.emit(f"Using Minecraft data directory: {self.minecraft_dir}")

            command = minecraft_launcher_lib.command.get_minecraft_command(
                version_id_to_launch, self.minecraft_dir, launch_options
            )

            if not self.options.get("executablePath"):
                java_path = command[0]
                if sys.platform == "win32" and "java.exe" in java_path.lower():
                    javaw_path = java_path.replace("java.exe", "javaw.exe")
                    if os.path.exists(javaw_path):
                        command[0] = javaw_path
                        self.log_message.emit(f"Switched to javaw.exe for game launch: {javaw_path}")
                    else:
                        self.log_message.emit(f"javaw.exe not found at {javaw_path}. Falling back to java.exe.")
            
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                cwd=self.minecraft_dir,
            )

            for line in iter(process.stdout.readline, ""):
                self.log_message.emit(line.strip())
            
            process.wait()

            exit_code = process.returncode
            if exit_code != 0:
                self.log_message.emit(f"Процесс завершился с кодом {exit_code}. Вероятно, произошла ошибка.")
                raise GameProcessError(f"Game process exited with code {exit_code}", exit_code)

            self.finished.emit("success", None)

        except Exception as e:
            error_details = {"message": str(e), "version_id": version_id_to_launch}
            lang = resources.LANGUAGES[self.lang]
            
            if isinstance(e, FileNotFoundError):
                error_details["type"] = "invalid_java_path"
                error_msg = lang['error_occurred'] + "Неверный путь к Java."
            
            elif isinstance(e, GameProcessError):
                if e.exit_code == 1:
                    error_details["type"] = "invalid_jvm_argument"
                    error_msg = lang['error_occurred'] + "Неверный аргумент или настройка JVM."
                else:
                    error_details["type"] = "file_corruption"
                    error_msg = lang['error_occurred'] + "Игра аварийно завершилась. Возможно, файлы повреждены."
            
            else:
                error_details["type"] = "generic"
                error_msg = f"{lang['error_occurred']}{e}"

            self.log_message.emit(f"ERROR: {error_msg}")
            import traceback
            self.log_message.emit(traceback.format_exc())
            self.finished.emit("error", error_details)

    def log_and_update_status(self, text):
        self.progress_update.emit(0, 1, text)
        self.log_message.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")