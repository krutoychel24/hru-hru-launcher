# hru_hru_launcher/core/mc_worker.py

import os
import sys
import uuid
import subprocess
import re
import traceback
import logging
import shutil
from datetime import datetime

from PySide6.QtCore import QThread, Signal
import minecraft_launcher_lib
from requests.exceptions import RequestException

from .profile_manager import create_launcher_profiles_if_needed, add_profile
from ..config import resources

class GameProcessError(Exception):
    def __init__(self, message, exit_code, output=""):
        super().__init__(message)
        self.exit_code = exit_code
        self.output = output

class InterruptedError(Exception):
    pass


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
        self._is_running = True
        self._versions_before_install = set()
        self._is_installing = False

    def stop(self):
        self.log_message.emit("Cancellation requested...")
        self._is_running = False
        
    def _get_stoppable_callback(self):
        lang_dict = resources.LANGUAGES[self.lang]
        
        def set_status(text):
            if not self._is_running: raise InterruptedError()
            self.log_and_update_status(text)
            
        def set_progress(value, max_value=0):
            if not self._is_running: raise InterruptedError()
            if max_value > 0:
                status_text = lang_dict.get('downloading_files', 'Downloading files')
                self.progress_update.emit(value, max_value, status_text)
        
        return { "setStatus": set_status, "setProgress": set_progress }

    def _detect_forge_id(self, versions, base_mc_version):
        build = self.mc_version.split("-")[-1]
        for v in versions:
            vid = v["id"] if isinstance(v, dict) else v
            if "forge" in vid and base_mc_version in vid and build in vid:
                return vid
        return None
        
    def _cleanup_interrupted_install(self):
        """Deletes partially installed version directory."""
        self.log_message.emit("Cleaning up partially installed files...")
        try:
            versions_after = {v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)}
            newly_created_versions = versions_after - self._versions_before_install
            
            if not newly_created_versions:
                self.log_message.emit("No new version folders found to clean up.")
                return

            for version_id in newly_created_versions:
                version_path = os.path.join(self.minecraft_dir, "versions", version_id)
                if os.path.isdir(version_path):
                    shutil.rmtree(version_path)
                    self.log_message.emit(f"Removed broken version directory: {version_id}")
            self.log_message.emit("Cleanup complete.")
        except Exception as e:
            self.log_message.emit(f"Cleanup failed: {e}")
            self.log_message.emit(traceback.format_exc())

    def run(self):
        version_id_to_launch = ""
        game_output = ""
        try:
            callback = self._get_stoppable_callback()
            
            create_launcher_profiles_if_needed(self.minecraft_dir, self.client_token)
            
            base_mc_version = self.mc_version.split("-")[0] if self.mod_loader == "forge" else self.mc_version

            if not self._is_running: raise InterruptedError()

            installed_version_ids = [v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)]
            
            self._is_installing = True
            self._versions_before_install = set(installed_version_ids)
            
            if base_mc_version not in installed_version_ids:
                self.log_and_update_status(f"Base version {base_mc_version} not found. Installing...")
                minecraft_launcher_lib.install.install_minecraft_version(base_mc_version, self.minecraft_dir, callback=callback)
            else:
                self.log_and_update_status(f"Base version {base_mc_version} already installed.")

            version_id_to_launch = base_mc_version
            profile_name = base_mc_version

            if self.mod_loader in ["fabric", "forge"]:
                mods_path = os.path.join(self.minecraft_dir, "mods")
                os.makedirs(mods_path, exist_ok=True)
                
                if not self._is_running: raise InterruptedError()

                if self.mod_loader == "fabric":
                    version_id_to_launch = minecraft_launcher_lib.fabric.install_fabric(base_mc_version, self.minecraft_dir, callback=callback)
                    profile_name = f"{base_mc_version} Fabric"
                
                elif self.mod_loader == "forge":
                    all_installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                    version_id_to_launch = self._detect_forge_id(all_installed, base_mc_version)
                    if not version_id_to_launch:
                        self.log_and_update_status(f"Installing Forge {self.mc_version}")
                        minecraft_launcher_lib.forge.install_forge_version(self.mc_version, self.minecraft_dir, callback=callback)
                        all_installed_after = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                        version_id_to_launch = self._detect_forge_id(all_installed_after, base_mc_version)
                        if not version_id_to_launch:
                            raise Exception(f"Could not find Forge version for {self.mc_version} after installation.")
                        self.log_and_update_status(f"New Forge version installed: {version_id_to_launch}")
                    else:
                        self.log_and_update_status(f"Found existing Forge version: {version_id_to_launch}")
                    profile_name = f"{base_mc_version} Forge"
            
            self._is_installing = False
            add_profile(self.minecraft_dir, version_id_to_launch, profile_name)

            custom_jvm_args = self.options.get("jvmArguments", [])
            all_jvm_args = [f"-Xmx{self.memory_gb}G", f"-Xms{self.memory_gb}G"] + custom_jvm_args
            
            launch_options = {
                "username": self.username, "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, self.username)), "token": "0",
                "jvmArguments": all_jvm_args, "fullscreen": self.fullscreen, "gameDirectory": self.minecraft_dir,
                "executablePath": self.options.get("executablePath"),
                "resolutionWidth": self.options.get("resolutionWidth"), "resolutionHeight": self.options.get("resolutionHeight"),
                "launchTarget": "minecraft"
            }
            launch_options = {k: v for k, v in launch_options.items() if v}

            if not self._is_running: raise InterruptedError()
            
            self.log_and_update_status(resources.LANGUAGES[self.lang]["starting"])
            command = minecraft_launcher_lib.command.get_minecraft_command(version_id_to_launch, self.minecraft_dir, launch_options)

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0), cwd=self.minecraft_dir)
            
            output_lines = []
            while self._is_running:
                if process.poll() is not None: break
                for line in iter(process.stdout.readline, ""):
                    if not line: break
                    clean_line = line.strip()
                    self.log_message.emit(clean_line)
                    output_lines.append(clean_line)
                self.msleep(50)
            
            game_output = "\n".join(output_lines)

            if not self._is_running:
                self.log_message.emit("Terminating game process...")
                process.terminate()
                process.wait(timeout=5)
                raise InterruptedError()

            exit_code = process.returncode
            if exit_code != 0:
                raise GameProcessError(f"Game process exited with code {exit_code}", exit_code, game_output)

            self.finished.emit("success", None)

        except InterruptedError:
            self.log_message.emit("Launch was successfully cancelled.")
            if self._is_installing:
                self._cleanup_interrupted_install()
            self.finished.emit("cancelled", None)
        except RequestException as e:
            error_msg = resources.LANGUAGES[self.lang].get("error_network_desc", "Could not connect to Mojang servers.")
            self.log_message.emit(f"ERROR: {error_msg} Details: {e}")
            self.finished.emit("error", {"type": "network_error", "message": error_msg})
        except Exception as e:
            error_details = {"message": str(e), "version_id": version_id_to_launch}
            
            if "Could not find net/minecraft/client/Minecraft.class" in game_output:
                error_details["type"] = "file_corruption"
            elif isinstance(e, GameProcessError):
                if e.exit_code == 1:
                    error_details["type"] = "invalid_jvm_argument"
                else:
                    error_details["type"] = "file_corruption"
            elif isinstance(e, FileNotFoundError):
                error_details["type"] = "invalid_java_path"
            else:
                error_details["type"] = "generic"

            self.log_message.emit(f"ERROR: An error occurred: {e}")
            self.log_message.emit(traceback.format_exc())
            self.finished.emit("error", error_details)

    def log_and_update_status(self, text):
        self.progress_update.emit(0, 0, text) 
        self.log_message.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")