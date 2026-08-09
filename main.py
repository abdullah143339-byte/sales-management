"""Sales & Inventory Management System - application entry point.

Run with:  python main.py
"""

from __future__ import annotations

import sys

from app_info import APP_NAME, APP_VERSION
from database.database import Database
from ui.login import LoginDialog
from ui.main_window import MainWindow
from ui.theme import QSS

from PySide6.QtWidgets import QApplication


def _check_updates(window) -> None:
    """Non-blocking update check shortly after the main window opens."""
    from services import updater

    url = updater.get_update_url(window.conn)
    if not url:
        return
    info = updater.fetch_latest(url)
    if updater.should_offer(window.conn, info):
        from ui.update_dialog import UpdateDialog

        UpdateDialog(window, window.conn, info).exec()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)

    db = Database()
    try:
        login = LoginDialog(db.conn)
        if login.exec() != LoginDialog.DialogCode.Accepted:
            return 0
        username = login.username
    except Exception:
        db.close()
        raise

    window = MainWindow(db, username)
    window.show()

    from PySide6.QtCore import QTimer

    QTimer.singleShot(3500, lambda: _check_updates(window))

    exit_code = app.exec()
    db.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
