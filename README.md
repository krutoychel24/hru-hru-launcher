# Hru Hru Launcher

Hru Hru Launcher is a custom Minecraft launcher built with Python and PySide6, providing a sleek interface for launching various Minecraft versions, including Vanilla, Forge, and Fabric. It features customizable settings, console output, and dynamic version loading.

---
## Features

* **Multi-Version Support:** Easily launch Vanilla, Forge, and Fabric versions of Minecraft.
* **User-Friendly Interface:** A clean and intuitive graphical user interface (GUI) built with PySide6.
* **Customizable Settings:** Adjust language (English/Russian), theme (Dark, Light, Neon), allocated memory, fullscreen mode, and launcher behavior after game launch.
* **Advanced JVM Arguments:** Option to enable G1GC for improved performance.
* **Dynamic Version Loading:** Automatically fetches available Minecraft versions (Vanilla, Forge, Fabric).
* **Integrated Console:** View real-time game output and launcher logs within the application.
* **Custom Data Directories:** Game runtime data (logs, saves, resource packs) are stored in a dedicated user-friendly folder, while core Minecraft installations remain in the standard `.minecraft` directory.
* **Modular Codebase:** The code has been split into organized modules for better maintainability and scalability.
* **Mod Installation (Alpha):** Basic implementation of mod installation support (early alpha).

---

### 👋 Contact me:

<p align="left">
  <a href="https://t.me/krutoychel24" target="_blank">
    <img src="https://img.shields.io/badge/Telegram-@krutoychel24-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="telegram"/>
  </a>
  <a href="https://discord.gg/t485rd37" target="_blank">
    <img src="https://img.shields.io/badge/Discord-HruHruStudio-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="discord"/>
  </a>
  <a href="mailto:krutoychel.info@gmail.com">
    <img src="https://img.shields.io/badge/Gmail-Write-D14836?style=for-the-badge&logo=gmail&logoColor=white" alt="gmail"/>
  </a>
</p>

## Preview

![Launcher Screenshot](https://i.postimg.cc/y8hygM23/Screenshot-2025-07-14-050917.png)

## Installation (for Developers)

To set up and run this project locally, follow these steps:

### Prerequisites

* **Python 3.11, 3.12, or 3.13:** It's recommended to use these Python versions for optimal compatibility with PyInstaller. You can download them from [python.org/downloads](https://www.python.org/downloads/). Ensure you add Python to your system's PATH during installation.
* **Java Runtime Environment (JRE) or Java Development Kit (JDK):** Minecraft requires Java to run. Ensure you have a compatible Java version installed on your system.

### Setup

1.  **Clone the repository** (or download the source code):
    ```bash
    git clone https://github.com/krutoychel24/hru-hru-launcher
    cd hru-hru-Launcher
    ```
2.  **Create a Virtual Environment** (highly recommended):
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment**:
    * **On Windows (Command Prompt):**
        ```bash
        .\venv\Scripts\activate
        ```
    * **On Windows (PowerShell):**
        ```bash
        .\venv\Scripts\Activate.ps1
        ```

4.  **Install the required Python packages**:
    ```bash
    pip install -r requirements.txt
    ```

---

## Running the Launcher (Development Mode)

After setting up the environment, you can run the launcher directly from the Python script:

```bash
python launcher.py
```

---
### Disclaimer

This is an unofficial Minecraft launcher. It is not affiliated with Mojang, Microsoft, or Minecraft.

The launcher supports offline mode for testing or singleplayer use only.

You must own a legal copy of Minecraft to use this launcher.

All Minecraft libraries are downloaded from official Mojang servers.
