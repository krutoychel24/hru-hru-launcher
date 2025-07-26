import os
import json
import uuid
from hru_hru_launcher.utils.paths import get_launcher_data_dir

SETTINGS_FILE_PATH = os.path.join(get_launcher_data_dir(), "launcher_settings.json")

def load_settings():
    """Loads launcher settings from the JSON file."""
    defaults = {
        "language": "en",
        "memory": 4,
        "fullscreen": False,
        "close_launcher": True,
        "last_username": "",
        "version_type": "vanilla",
        "last_version": "",
        "accent_color": "#1DB954",
        "last_tab": 0,
        "window_geometry": "",
        "jvm_args": "",
        "java_path": "",
        "clientToken": uuid.uuid4().hex,
    }
    
    if os.path.exists(SETTINGS_FILE_PATH):
        try:
            with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            for key, value in defaults.items():
                if key not in settings:
                    settings[key] = value
            return settings
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading settings: {e}. Using defaults.")
            defaults["clientToken"] = uuid.uuid4().hex
            return defaults
    return defaults

def save_settings(settings_dict):
    """Saves launcher settings to the JSON file."""
    try:
        with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Error saving settings: {e}")