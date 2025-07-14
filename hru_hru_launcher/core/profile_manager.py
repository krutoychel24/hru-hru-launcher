# hru_hru_launcher/core/profile_manager.py
import os
import json
import uuid
from datetime import datetime, timezone

def create_launcher_profiles_if_needed(minecraft_dir: str, client_token: str):
    profiles_path = os.path.join(minecraft_dir, "launcher_profiles.json")
    if not os.path.exists(profiles_path):
        base_structure = {
            "profiles": {},
            "settings": {
                "locale": "ru_ru",
                "enableSnapshots": True,
                "enableAdvanced": False,
            },
            "version": 2,
            "clientToken": client_token,
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
            "type": "custom",
        }

        data["profiles"][profile_id] = new_profile
        data["selectedProfile"] = profile_id

        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
        print(f"Profile '{profile_name}' added.")