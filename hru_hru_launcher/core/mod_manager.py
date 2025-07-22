import requests
import os
import json
import zipfile
import logging

try:
    import tomllib as tomli
except ImportError:
    import tomli

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODRINTH_API_URL = "https://api.modrinth.com/v2"

def search_mods(query: str, game_version: str, loader: str, sort_option: str = "relevance"):
    """
    Поиск модов на Modrinth по заданным параметрам.
    """
    params = {
        "query": query,
        "facets": json.dumps([
            [f"versions:{game_version}"],
            [f"project_type:mod"]
        ]),
        "loaders": json.dumps([loader.lower()]),
        "limit": 20,
        "index": sort_option
    }
    try:
        response = requests.get(f"{MODRINTH_API_URL}/search", params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("hits", [])
    except requests.RequestException as e:
        logging.error(f"Ошибка при поиске модов ('{query}'): {e}")
        return []

def get_project_details(project_id: str):
    """
    Получение детальной информации о проекте по его ID.
    """
    if not project_id: return None
    try:
        response = requests.get(f"{MODRINTH_API_URL}/project/{project_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Не удалось получить детали проекта {project_id}: {e}")
        return None

def get_mod_id_from_jar(jar_path: str):
    """
    Извлечение ID проекта Modrinth из метаданных .jar файла.
    """
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            if 'fabric.mod.json' in jar.namelist():
                with jar.open('fabric.mod.json') as f:
                    data = json.load(f)
                    custom_data = data.get("custom", {})
                    return custom_data.get("modrinth", {}).get("project_id") or data.get('id')
            elif 'META-INF/mods.toml' in jar.namelist():
                with jar.open('META-INF/mods.toml', 'r') as f:
                    # tomli.load() ожидает бинарный файл, поэтому используем 'rb'
                    # Но так как мы уже открыли файл как текстовый, декодируем его
                    data = tomli.loads(f.read().decode('utf-8'))
                    if 'mods' in data and len(data['mods']) > 0:
                        return data['mods'][0].get('modId')
    except (zipfile.BadZipFile, json.JSONDecodeError, tomli.TOMLDecodeError, KeyError, IndexError, AttributeError) as e:
        logging.warning(f"Не удалось прочитать mod ID из {os.path.basename(jar_path)}: {e}")
        return None
    return None

def get_latest_mod_version(project_id: str, game_version: str, loader: str):
    """
    Получение последней совместимой версии файла мода.
    """
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
        logging.error(f"Не удалось найти версию для {project_id} (MC {game_version}, {loader}): {e}")
        return None
    return None

def download_file(url: str, destination_folder: str, file_name: str, progress_callback):
    """
    Скачивание файла с отображением прогресса.
    """
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
        logging.info(f"Файл {file_name} успешно скачан.")
        return True
    except (requests.RequestException, IOError) as e:
        logging.error(f"Ошибка скачивания {file_name}: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        return False
