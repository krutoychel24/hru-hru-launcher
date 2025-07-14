# hru_hru_launcher/utils/paths.py
import os
import sys

def get_documents_path():
    """Returns the path to the user's Documents folder."""
    if sys.platform == "win32":
        import ctypes.wintypes
        CSIDL_PERSONAL = 5
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(
            None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf
        )
        return buf.value
    elif sys.platform == "darwin":  
        return os.path.expanduser("~/Documents")
    else:  
        return os.path.expanduser("~/Documents")

def get_launcher_data_dir():
    """Returns the path to the custom launcher data directory."""
    documents_path = get_documents_path()
    launcher_dir = os.path.join(documents_path, "Hru Hru Studio", "Hru Hru Launcher")
    os.makedirs(launcher_dir, exist_ok=True)
    return launcher_dir

def get_assets_dir():
    """Returns the path to the assets directory."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "assets")
    else:
        return os.path.join(os.path.dirname(__file__), '..', '..', 'assets')