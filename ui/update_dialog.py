"""Update-available dialog: download + install on Windows, open link elsewhere."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app_info import APP_NAME
from database import models
from services import updater
from ui.widgets import label, make_button

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QVBoxLayout


class UpdateDialog(QDialog):
    """Shows what is new and lets the user install the update."""

    def __init__(self, parent, conn, info: dict):
        super().__init__(parent)
        self.conn = conn
        self.info = info
        self.setWindowTitle("Update Available")
        self.setMinimumSize(460, 330)

        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(label(
            f"Version {info['version']} is available", size=16, bold=True, color="#1f2a3d"
        ))
        lay.addWidget(label(
            f"You are running version {updater.APP_VERSION} of {APP_NAME}.",
            size=12, color="#64748b",
        ))

        notes = (info.get("notes") or "").strip()
        if notes:
            from PySide6.QtWidgets import QTextBrowser

            browser = QTextBrowser()
            browser.setPlainText(notes)
            browser.setFixedHeight(120)
            browser.setStyleSheet("background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;")
            lay.addWidget(browser)

        self.status = label("", size=12, color="#64748b")
        lay.addWidget(self.status)

        row = QHBoxLayout()
        install_btn = make_button("Download & Install", "", self._install)
        skip_btn = make_button("Skip This Version", "secondary", self._skip)
        later_btn = make_button("Later", "secondary", self.accept)
        row.addWidget(install_btn)
        row.addWidget(skip_btn)
        row.addWidget(later_btn)
        lay.addLayout(row)

    # ------------------------------------------------------------------

    def _install(self):
        url = self.info.get("windows_url") or self.info.get("android_url")
        if not url:
            self.status.setText("No download link available for this device.")
            return
        if sys.platform.startswith("win") and getattr(sys, "frozen", False):
            self._download_and_replace(url)
        else:
            QDesktopServices.openUrl(QUrl(url))
            self.accept()

    def _download_and_replace(self, url: str):
        app_dir = updater.app_executable_dir()
        app_exe = Path(sys.executable)
        new_file = app_dir / (app_exe.stem + ".new" + app_exe.suffix)

        self.status.setText("Downloading update...")
        QApplication.processEvents()
        if not updater.download(url, new_file):
            self.status.setText("Download failed. Please try again later.")
            return

        script = app_dir / "updater.bat"
        script.write_text(
            updater.updater_batch(script, new_file, app_exe),
            encoding="utf-8",
        )
        try:
            subprocess.Popen(["cmd", "/c", str(script)], cwd=str(app_dir))
        except OSError:
            self.status.setText("Could not start the installer. Please run the app again.")
            return
        self.accept()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _skip(self):
        models.set_setting(self.conn, updater.SKIP_KEY, self.info["version"])
        self.accept()
