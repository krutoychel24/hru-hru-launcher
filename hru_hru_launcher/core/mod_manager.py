import requests
import os
import json
import zipfile
import logging

try:
    import tomllib
except ImportError:
    import tomli

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODRINTH_API_URL = "https://api.modrinth.com/v2"

def search_mods(query: str, game_version: str, loader: str, lang_dict: dict, sort_option: str = "relevance", offset: int = 0):
    facets = [
        [f"versions:{game_version}"],
        [f"project_type:mod"],
        [f"categories:{loader.lower()}"]
    ]
    params = {
        "query": query,
        "facets": json.dumps(facets),
        "limit": 20, 
        "index": sort_option,
        "offset": offset 
    }
    try:
        response = requests.get(f"{MODRINTH_API_URL}/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("hits", []), data.get("total_hits", 0) 
    except requests.RequestException as e:
        error_message = lang_dict.get("error_searching_mods", "Error searching for mods ('{query}'): {e}")
        logging.error(error_message.format(query=query, e=e))
        return [], 0

def get_project_details(project_id: str, lang_dict: dict):
    if not project_id: return None
    try:
        response = requests.get(f"{MODRINTH_API_URL}/project/{project_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        error_message = lang_dict.get("error_getting_project_details", "Failed to get project details for {project_id}: {e}")
        logging.error(error_message.format(project_id=project_id, e=e))
        return None

def get_mod_id_from_jar(jar_path: str, lang_dict: dict):
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            if 'fabric.mod.json' in jar.namelist():
                with jar.open('fabric.mod.json') as f:
                    data = json.load(f)
                    custom_data = data.get("custom", {})
                    return custom_data.get("modrinth", {}).get("project_id") or data.get('id')
            elif 'META-INF/mods.toml' in jar.namelist():
                with jar.open('META-INF/mods.toml', 'r') as f:
                    data = tomllib.loads(f.read().decode('utf-8')) if hasattr(tomllib, 'loads') else tomli.loads(f.read().decode('utf-8'))
                    if 'mods' in data and len(data['mods']) > 0:
                        return data['mods'][0].get('modId')
    except (zipfile.BadZipFile, json.JSONDecodeError, tomli.TOMLDecodeError, KeyError, IndexError, AttributeError) as e:
        error_message = lang_dict.get("error_reading_mod_id", "Could not read mod ID from {filename}: {e}")
        logging.warning(error_message.format(filename=os.path.basename(jar_path), e=e))
        return None
    return None

def get_latest_mod_version(project_id: str, game_version: str, loader: str, lang_dict: dict):
    params = {
        "game_versions": json.dumps([game_version]),
        "loaders": json.dumps([loader.lower()])
    }
    try:
        response = requests.get(f"{MODRINTH_API_URL}/project/{project_id}/version", params=params, timeout=10)
        response.raise_for_status()
        versions = response.json()
        if versions and versions[0].get("files"):
            return versions[0]
    except requests.RequestException as e:
        error_message = lang_dict.get("error_finding_mod_version", "Could not find a version for {project_id} (MC {game_version}, {loader}): {e}")
        logging.error(error_message.format(project_id=project_id, game_version=game_version, loader=loader, e=e))
        return None
    return None

def download_file(url: str, destination_folder: str, file_name: str, progress_callback, lang_dict: dict):
    os.makedirs(destination_folder, exist_ok=True)
    file_path = os.path.join(destination_folder, file_name)
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            bytes_downloaded = 0
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    if total_size > 0:
                        progress = int((bytes_downloaded / total_size) * 100)
                        progress_callback(progress)
            progress_callback(100)
        success_message = lang_dict.get("file_downloaded_successfully", "File {filename} downloaded successfully.")
        logging.info(success_message.format(filename=file_name))
        return True
    except (requests.RequestException, IOError) as e:
        error_message = lang_dict.get("error_downloading_file", "Error downloading {filename}: {e}")
        logging.error(error_message.format(filename=file_name, e=e))
        if os.path.exists(file_path):
            os.remove(file_path)
        return False