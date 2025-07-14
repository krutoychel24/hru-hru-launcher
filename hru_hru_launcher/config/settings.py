# hru_hru_launcher/config/settings.py
import os
import json
import uuid
from hru_hru_launcher.utils.paths import get_launcher_data_dir

SETTINGS_FILE_PATH = os.path.join(get_launcher_data_dir(), "launcher_settings.json")

def load_settings():
    """Loads launcher settings from the JSON file."""
    defaults = {
        "language": "ru",
        "theme": "dark",
        "memory": 4,
        "fullscreen": False,
        "close_launcher": True,
        "last_username": "",
        "use_g1gc": False,
        "version_type": "vanilla",
        "last_version": "",
        "clientToken": uuid.uuid4().hex,
    }
    if os.path.exists(SETTINGS_FILE_PATH):
        try:
            with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            defaults.update(settings)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}. Using defaults.")
    return defaults

def save_settings(settings_dict):
    """Saves launcher settings to the JSON file."""
    with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(settings_dict, f, ensure_ascii=False, indent=4)