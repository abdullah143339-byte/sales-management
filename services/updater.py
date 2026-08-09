"""Automatic update checking and downloading.

The app periodically asks a version manifest URL (stored in Settings) for the
latest version. When a newer version exists it offers to download it. On
Windows the new .exe replaces the current one and the app restarts; on other
platforms (e.g. Android) the download URL is opened so the user can install
the new package.

The manifest is a small JSON file, e.g.::

    {
        "version": "1.0.1",
        "notes": "Bug fixes",
        "windows_url": "https://example.com/app-1.0.1.exe",
        "android_url": "https://example.com/app-1.0.1.apk"
    }
"""

from __future__ import annotations

import json
import platform
import sys
import urllib.request
from pathlib import Path

from app_info import APP_VERSION

UPDATE_URL_KEY = "update_url"
SKIP_KEY = "skipped_version"

_TIMEOUT = 15


def _parse_version(text: str):
    return tuple(int(x) for x in text.strip().split(".") if x.isdigit()) or (0,)


def is_newer(remote: str, current: str = APP_VERSION) -> bool:
    """True when the remote version is newer than the current one."""
    return _parse_version(remote) > _parse_version(current)


def should_offer(conn, info) -> bool:
    """True when the manifest describes a version worth offering."""
    from database import models

    if not info or not is_newer(info.get("version", "")):
        return False
    if info.get("version") == models.get_setting(conn, SKIP_KEY):
        return False
    return True


def get_update_url(conn) -> str:
    from database import models

    return (models.get_setting(conn, UPDATE_URL_KEY, "") or "").strip()


def fetch_latest(update_url: str):
    """Fetch the manifest and return it as a dict, or None on failure.

    Never raises: network problems and bad JSON simply yield None so a broken
    link never blocks the app.
    """
    if not update_url:
        return None
    try:
        req = urllib.request.Request(update_url, headers={"User-Agent": "SalesManagement/" + APP_VERSION})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if not isinstance(data, dict) or not data.get("version"):
            return None
        return data
    except Exception:  # noqa: BLE001 - update checks must never crash the app
        return None


def _platform_key():
    if platform.system() == "Windows":
        return "windows_url"
    if sys.platform.startswith("android"):
        return "android_url"
    return "windows_url"


def download(url: str, dest: Path) -> bool:
    """Download a file to dest, returning success. Never raises."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SalesManagement/" + APP_VERSION})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp, open(dest, "wb") as fh:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
        return dest.exists() and dest.stat().st_size > 0
    except Exception:  # noqa: BLE001
        try:
            dest.unlink()
        except OSError:
            pass
        return False


def app_executable_dir() -> Path:
    """Folder containing the running executable (for self-update)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def updater_batch(script: Path, new_file: Path, app_exe: Path) -> str:
    """Return a .bat script that replaces the running exe and relaunches it."""
    return (
        f'@echo off\n'
        f'timeout /t 1 /nobreak >nul\n'
        f'echo Updating {app_exe.name}...\n'
        f'taskkill /f /im {app_exe.name} >nul 2>&1\n'
        f'copy /y "{new_file}" "{app_exe}" >nul\n'
        f'if errorlevel 1 (\n'
        f'  echo Update failed. Please run the app again.\n'
        f'  timeout /t 5 /nobreak >nul\n'
        f'  exit /b 1\n'
        f')\n'
        f'del /q "{script.name}" "{new_file}" >nul 2>&1\n'
        f'start "" "{app_exe}"\n'
    )
