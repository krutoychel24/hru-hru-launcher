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

def get_mod_metadata_from_jar(jar_path: str, lang_dict: dict):
    metadata = {
        "name": os.path.basename(jar_path),
        "version": "Unknown",
        "game_version": "Unknown",
        "mod_id": None,
        "author": "Unknown",
        "modrinth_project_id": None,
        "icon_path_in_jar": None,
        "icon_data": None
    }
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            if 'fabric.mod.json' in jar.namelist():
                with jar.open('fabric.mod.json') as f:
                    data = json.load(f)
                    metadata["name"] = data.get('name', metadata["name"])
                    metadata["version"] = data.get('version', metadata["version"])
                    metadata["mod_id"] = data.get('id')
                    
                    depends = data.get('depends', {})
                    mc_version = depends.get('minecraft', '*')
                    metadata["game_version"] = mc_version if mc_version != '*' else 'Unknown'

                    authors = data.get('authors', [])
                    if authors:
                        if isinstance(authors[0], dict):
                            metadata["author"] = ', '.join([a.get('name', 'Unknown') for a in authors])
                        else:
                            metadata["author"] = ', '.join(authors)

                    custom_data = data.get("custom", {})
                    metadata["modrinth_project_id"] = custom_data.get("modrinth", {}).get("project_id")
                    
                    icon_path = data.get('icon')
                    if icon_path and icon_path in jar.namelist():
                        metadata["icon_path_in_jar"] = icon_path
                        with jar.open(icon_path) as icon_file:
                            metadata["icon_data"] = icon_file.read()

            elif 'META-INF/mods.toml' in jar.namelist():
                with jar.open('META-INF/mods.toml', 'r') as f:
                    data = tomllib.loads(f.read().decode('utf-8')) if hasattr(tomllib, 'loads') else tomli.loads(f.read().decode('utf-8'))
                    
                    dependencies = data.get('dependencies', {}).get(data.get('mods', [{}])[0].get('modId', ''), [])
                    for dep in dependencies:
                        if dep.get('modId') == 'minecraft':
                            metadata["game_version"] = dep.get('versionRange', 'Unknown').strip('[]()')
                            break

                    if 'mods' in data and len(data['mods']) > 0:
                        mod_info = data['mods'][0]
                        metadata["name"] = mod_info.get('displayName', metadata["name"])
                        metadata["version"] = mod_info.get('version', metadata["version"])
                        metadata["mod_id"] = mod_info.get('modId')
                        metadata["author"] = mod_info.get('authors', metadata["author"])

    except Exception as e:
        error_message = lang_dict.get("error_reading_mod_id", "Could not read metadata from {filename}: {e}")
        logging.warning(error_message.format(filename=os.path.basename(jar_path), e=e))
    return metadata

def scan_local_mods(mods_folder: str, lang_dict: dict, installed_mods_data: dict):
    installed_mods = []
    if not os.path.exists(mods_folder):
        return []
    
    # Create a lookup map from filename to its saved data
    filename_map = {v['filename']: v for v in installed_mods_data.values() if 'filename' in v}
    
    project_ids_to_fetch = []
    mod_infos_temp = []

    # First pass: gather metadata from JARs and use saved data if available
    for filename in os.listdir(mods_folder):
        file_path = os.path.join(mods_folder, filename)
        if filename.endswith((".jar", ".jar.disabled")):
            mod_info = get_mod_metadata_from_jar(file_path, lang_dict)
            mod_info["filepath"] = file_path
            mod_info["enabled"] = not filename.endswith(".jar.disabled")

            # If this file is in our saved data, use that data as the source of truth
            if filename in filename_map:
                saved_info = filename_map[filename]
                mod_info['modrinth_project_id'] = saved_info.get('project_id')
                mod_info['game_version'] = saved_info.get('game_version', mod_info['game_version'])

            mod_infos_temp.append(mod_info)
            if mod_info.get("modrinth_project_id") and not mod_info.get("icon_data"):
                project_ids_to_fetch.append(mod_info["modrinth_project_id"])

    # Fetch project details from Modrinth in bulk for mods that need an icon_url
    if project_ids_to_fetch:
        try:
            # Remove duplicates
            unique_project_ids = list(set(project_ids_to_fetch))
            params = {"ids": json.dumps(unique_project_ids)}
            response = requests.get(f"{MODRINTH_API_URL}/projects", params=params, timeout=15)
            response.raise_for_status()
            projects_data = response.json()
            project_details_map = {project['id']: project for project in projects_data}
        except requests.RequestException as e:
            logging.error(f"Failed to fetch bulk project details: {e}")
            project_details_map = {}
    else:
        project_details_map = {}

    # Second pass: enrich mod_info with fetched icon URLs
    for mod_info in mod_infos_temp:
        project_id = mod_info.get("modrinth_project_id")
        if project_id and project_id in project_details_map:
            project_details = project_details_map[project_id]
            mod_info["icon_url"] = project_details.get("icon_url")
        
        installed_mods.append(mod_info)

    return installed_mods