import os
import sys
import uuid
import subprocess
import json
import urllib.request
import zipfile
from datetime import datetime

from PySide6.QtCore import QThread, Signal
import minecraft_launcher_lib

from .profile_manager import create_launcher_profiles_if_needed, add_profile
from ..config.resources import LANGUAGES


class MinecraftWorker(QThread):
    progress_update = Signal(int, int, str)
    finished = Signal(str)
    log_message = Signal(str)

    def __init__(
        self,
        mc_version,
        username,
        minecraft_dir,
        client_token,
        memory_gb=2,
        fullscreen=False,
        jvm_args=None,
        lang="ru",
        mod_loader=None,
    ):
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
                value, 100, f"{LANGUAGES[self.lang]['downloading']} {value}%"
            ),
            "setMax": lambda value: None,
        }
        try:
            create_launcher_profiles_if_needed(self.minecraft_dir, self.client_token)
            
            base_mc_version = (
                self.mc_version.split("-")[0]
                if self.mod_loader == "forge"
                else self.mc_version
            )
            self.log_and_update_status(f"Checking base version: {base_mc_version}")
            
            minecraft_launcher_lib.install.install_minecraft_version(
                base_mc_version, self.minecraft_dir, callback=callback
            )

            base_version_path = os.path.join(
                self.minecraft_dir, "versions", base_mc_version
            )
            base_json_path = os.path.join(base_version_path, f"{base_mc_version}.json")
            if not os.path.isfile(base_json_path):
                raise Exception(
                    f"Base version {base_mc_version} is not installed correctly (no {base_mc_version}.json)."
                )

            version_id_to_launch = base_mc_version
            profile_name = base_mc_version

            if self.mod_loader in ["fabric", "forge"]:
                mods_path = os.path.join(self.minecraft_dir, "mods")
                if not os.path.exists(mods_path):
                    os.makedirs(mods_path)
                    self.log_and_update_status(f"Created 'mods' folder")

                if self.mod_loader == "fabric":
                    self.log_and_update_status(f"Installing Fabric for {base_mc_version}")
                    minecraft_launcher_lib.fabric.install_fabric(
                        base_mc_version, self.minecraft_dir, callback=callback
                    )
                    installed_versions = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                    fabric_versions = [
                        v for v in installed_versions
                        if v["id"].startswith(f"fabric-loader-") and base_mc_version in v["id"]
                    ]
                    if not fabric_versions:
                        raise Exception(f"Fabric for Minecraft {base_mc_version} not found.")
                    version_id_to_launch = fabric_versions[0]["id"]
                    profile_name = f"{base_mc_version} Fabric"
                
                elif self.mod_loader == "forge":
                    self.log_and_update_status(f"Installing Forge {self.mc_version}")
                    versions_before = {v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)}
                    
                    try:
                        minecraft_launcher_lib.forge.install_forge_version(
                            self.mc_version, self.minecraft_dir, callback=callback
                        )
                    except Exception as forge_install_error:
                        self.log_message.emit(f"Forge installation failed: {forge_install_error}. Trying to find existing version.")

                    versions_after = {v["id"] for v in minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)}
                    new_versions = versions_after - versions_before

                    if new_versions:
                        version_id_to_launch = new_versions.pop()
                        self.log_and_update_status(f"New Forge version installed: {version_id_to_launch}")
                    else:
                        all_installed = minecraft_launcher_lib.utils.get_installed_versions(self.minecraft_dir)
                        version_id_to_launch = self._detect_forge_id(all_installed, base_mc_version)
                        if version_id_to_launch:
                            self.log_and_update_status(f"Found existing Forge version: {version_id_to_launch}")
                        else:
                            raise Exception(f"Could not find or install Forge version for {self.mc_version}")
                    
                    profile_name = f"{base_mc_version} Forge"

            add_profile(self.minecraft_dir, version_id_to_launch, profile_name)

            all_jvm_args = [f"-Xmx{self.memory_gb}G", f"-Xms{self.memory_gb}G"]
            if self.jvm_args.get("use_g1gc", False):
                all_jvm_args.extend([
                    "-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=200",
                    "-XX:+UnlockExperimentalVMOptions", "-XX:+DisableExplicitGC", "-XX:+AlwaysPreTouch",
                    "-XX:G1NewSizePercent=30", "-XX:G1MaxNewSizePercent=40", "-XX:G1HeapRegionSize=8M",
                    "-XX:G1ReservePercent=20", "-XX:G1HeapWastePercent=5", "-XX:G1MixedGCCountTarget=4",
                    "-XX:InitiatingHeapOccupancyPercent=15", "-XX:G1MixedGCLiveThresholdPercent=90",
                    "-XX:G1RSetUpdatingPauseTimePercent=5", "-XX:SurvivorRatio=32",
                    "-XX:+PerfDisableSharedMem", "-XX:MaxTenuringThreshold=1",
                ])

            options = {
                "username": self.username,
                "uuid": str(uuid.uuid3(uuid.NAMESPACE_DNS, self.username)),
                "token": "0",
                "jvmArguments": all_jvm_args,
                "fullscreen": self.fullscreen,
                "gameDirectory": self.minecraft_dir,
            }

            self.log_and_update_status(LANGUAGES[self.lang]["starting"])
            self.log_message.emit(f"Using Minecraft data directory: {self.minecraft_dir}")

            command = minecraft_launcher_lib.command.get_minecraft_command(
                version_id_to_launch, self.minecraft_dir, options
            )

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
                cwd=options.get("gameDirectory"),
            )

            for line in iter(process.stdout.readline, ""):
                self.log_message.emit(line.strip())
            process.wait()
            self.finished.emit("success")
        except Exception as e:
            error_msg = f"{LANGUAGES[self.lang]['error_occurred']}{e}"
            self.log_message.emit(f"ERROR: {error_msg}")
            import traceback
            self.log_message.emit(traceback.format_exc())
            self.finished.emit(error_msg)

    def log_and_update_status(self, text):
        self.progress_update.emit(0, 1, text)
        self.log_message.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")