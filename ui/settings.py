"""Settings page: change admin password, update settings and app info."""

from __future__ import annotations

from app_info import APP_NAME, APP_VERSION
from database import models
from services import updater
from ui.widgets import form_row, label, make_button, notify, page_header
from utils.validation import validate_username

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget


class SettingsPage(QWidget):
    def __init__(self, conn, username, db_path, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.username = username
        self.db_path = db_path

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        self.page_title = page_header("Settings")
        root.addWidget(self.page_title)
        root.addSpacing(12)

        box = QGroupBox("Change Password")
        v = QVBoxLayout(box)
        self.old_edit = QLineEdit()
        self.old_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_edit = QLineEdit()
        self.new_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)

        v.addLayout(form_row([("Current Password:", self.old_edit)]))
        v.addLayout(form_row([("New Password:", self.new_edit)]))
        v.addLayout(form_row([("Confirm New Password:", self.confirm_edit)]))
        v.addWidget(make_button("Change Password", "", self.change_password))
        v.addWidget(label(
            "New password must be at least 6 characters. It is stored using PBKDF2 hashing.",
            size=11, color="#94a3b8",
        ))
        root.addWidget(box)
        root.addSpacing(12)

        ub = QGroupBox("Updates")
        uv = QVBoxLayout(ub)
        self.update_url_edit = QLineEdit()
        self.update_url_edit.setPlaceholderText("https://raw.githubusercontent.com/.../version.json")
        self.update_url_edit.setText(updater.get_update_url(self.conn))
        uv.addLayout(form_row([("Update URL:", self.update_url_edit)]))
        uv.addWidget(label(
            "Where the app looks for new versions. Leave empty to disable update checks.",
            size=11, color="#94a3b8",
        ))
        uv.addLayout(self._update_buttons())
        root.addWidget(ub)
        root.addSpacing(12)

        info = QGroupBox("Application Information")
        vi = QVBoxLayout(info)
        vi.addWidget(label(f"{APP_NAME}  |  Version: {APP_VERSION}", size=12, color="#334155"))
        vi.addWidget(label(f"Logged in as:  {self.username}", size=12, color="#334155"))
        vi.addWidget(label(f"Database file:  {self.db_path}", size=12, color="#334155"))
        root.addWidget(info)
        root.addStretch()

    def _update_buttons(self):
        row = QHBoxLayout()
        row.addWidget(make_button("Save Update URL", "secondary", self.save_update_url))
        row.addWidget(make_button("Check for Updates", "", self.check_updates))
        row.addStretch()
        return row

    def play_entrance(self):
        from ui.animations import fade_in

        fade_in(self.page_title, 350)

    def change_password(self):
        old = self.old_edit.text()
        new = self.new_edit.text()
        confirm_txt = self.confirm_edit.text()

        if not models.verify_login(self.conn, self.username, old):
            notify(self, "Current password is incorrect.", "Error", error=True)
            return
        if len(new) < 6:
            notify(self, "New password must be at least 6 characters.", "Error", error=True)
            return
        if new != confirm_txt:
            notify(self, "New password and confirmation do not match.", "Error", error=True)
            return
        models.change_password(self.conn, self.username, new)
        self.old_edit.clear()
        self.new_edit.clear()
        self.confirm_edit.clear()
        notify(self, "Password changed successfully.", "Success")

    def save_update_url(self):
        url = self.update_url_edit.text().strip()
        models.set_setting(self.conn, updater.UPDATE_URL_KEY, url)
        notify(self, "Update URL saved.", "Success")

    def check_updates(self):
        url = updater.get_update_url(self.conn)
        if not url:
            self.save_update_url()
            url = updater.get_update_url(self.conn)
        info = updater.fetch_latest(url)
        if info and updater.should_offer(self.conn, info):
            from ui.update_dialog import UpdateDialog

            UpdateDialog(self, self.conn, info).exec()
        elif info and not updater.is_newer(info.get("version", "")):
            notify(self, "You are already running the latest version.", "No Updates")
        else:
            notify(
                self,
                "Could not reach the update server. Check the Update URL and try again.",
                "No Updates",
                error=True,
            )
