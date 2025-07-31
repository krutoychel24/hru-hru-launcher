# helpers.py
import math
import re

def format_size(size_bytes):
    if size_bytes <= 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    try:
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
    except (ValueError, IndexError):
        return "0 B"

def version_key(version_string):
    parts = []
    for part in version_string.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0) 
    return parts

def get_base_version(version_id):
    version_id_lower = version_id.lower()

    if 'fabric' in version_id_lower:
        matches = re.findall(r"(\d+\.\d+(\.\d+)?)", version_id)
        if matches:
            return matches[-1][0]

    match = re.match(r"(\d+\.\d+(\.\d+)?)", version_id)
    if match:
        return match.group(1)

    return version_id 

def get_version_type(version_id):
    version_id_lower = version_id.lower()
    if "fabric" in version_id_lower:
        return "Fabric"
    if "forge" in version_id_lower:
        return "Forge"
    return "Vanilla"

def get_latest_versions(raw_versions):
    latest_versions = {}
    for version_str in raw_versions:
        if '-' not in version_str:
            continue
        mc_version = version_str.split('-', 1)[0]
        if mc_version not in latest_versions:
            latest_versions[mc_version] = version_str
    return list(latest_versions.values())