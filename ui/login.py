"""Admin login dialog with password change on first login."""

from __future__ import annotations

import os

from database import models
from ui.animations import add_shadow, fade_in, rise_card, shake
from ui.theme import QSS
from ui.widgets import label
from utils.validation import validate_username

from PySide6.QtCore import QSizeF, Qt, QUrl
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

def _asset_path(name: str):
    """Resolve a file inside ``assets/`` whether frozen or running from source."""
    import sys

    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", name)


_VIDEO_PATH = _asset_path("login_bg.mp4")


class LoginDialog(QDialog):
    """Modal login window with a video background. Returns the username on accept."""

    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.username = None
        self._shown = False
        self.setWindowTitle("Login - Sales Management System")
        self.setFixedSize(920, 600)
        self.setStyleSheet(QSS)

        self._setup_video()

        # Light overlay so the glass card stays readable on the video.
        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.overlay.setStyleSheet("background: rgba(8, 15, 35, 110);")
        self.overlay.setGeometry(0, 0, self.width(), self.height())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()

        self.form = QWidget()
        self.form.setObjectName("card")
        layout = QVBoxLayout(self.form)
        layout.setContentsMargins(34, 32, 34, 28)
        layout.setSpacing(12)

        title = label("Sales Management System", size=22, bold=True, color="#1f2a3d")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = label("Sign in to continue", size=12, color="#64748b")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addSpacing(12)

        layout.addWidget(label("Username", size=12, color="#334155"))
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter username")
        layout.addWidget(self.username_edit)

        layout.addWidget(label("Password", size=12, color="#334155"))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Enter password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_edit)

        self.error_label = label("", size=12, color="#dc2626")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        self.login_btn = QPushButton("Login")
        self.login_btn.setMinimumHeight(42)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self.try_login)
        layout.addWidget(self.login_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        note = label(
            "Default credentials (first run):\nUsername: admin  |  Password: admin123",
            size=11,
            color="#94a3b8",
        )
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

        center_box = QHBoxLayout()
        center_box.addStretch()
        center_box.addWidget(self.form, 0)
        center_box.addStretch()
        outer.addLayout(center_box)
        outer.addStretch()

        add_shadow(self.form, blur=28, y_offset=6, alpha=55)

        self.username_edit.setFocus()
        self.password_edit.returnPressed.connect(self.try_login)

    def _setup_video(self):
        """Play the background video if available; fail silently otherwise.

        Uses QGraphicsVideoItem inside a QGraphicsView instead of QVideoWidget
        because QVideoWidget ignores z-order on Windows and would cover the
        login card. QGraphicsView is a normal widget, so the card and overlay
        always render on top of it.
        """
        self._video_ok = False
        if not os.path.exists(_VIDEO_PATH):
            return
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
            from PySide6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

            self.video_view = QGraphicsView(self)
            self.video_view.setGeometry(0, 0, self.width(), self.height())
            self.video_view.setFrameShape(QFrame.Shape.NoFrame)
            self.video_view.setStyleSheet("background: black; border: none;")
            self.video_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.video_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.video_view.setScene(QGraphicsScene(self.video_view))
            self.video_view.lower()

            self.video_item = QGraphicsVideoItem()
            self.video_item.setSize(QSizeF(self.width(), self.height()))
            self.video_view.scene().addItem(self.video_item)

            self.player = QMediaPlayer(self)
            audio = QAudioOutput(self)
            audio.setVolume(0)
            self.player.setAudioOutput(audio)
            self.player.setVideoOutput(self.video_item)
            self.player.setSource(QUrl.fromLocalFile(_VIDEO_PATH))
            self.player.setLoops(QMediaPlayer.Loops.Infinite)
            self.player.play()
            self._video_ok = True
        except Exception:  # noqa: BLE001 - video is cosmetic, never block login
            self._video_ok = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "video_view", None) is not None:
            self.video_view.setGeometry(0, 0, self.width(), self.height())
            self.video_item.setSize(QSizeF(self.width(), self.height()))
        if getattr(self, "overlay", None) is not None:
            self.overlay.setGeometry(0, 0, self.width(), self.height())

    def showEvent(self, event):
        super().showEvent(event)
        if not self._shown:
            self._shown = True
            rise_card(self.form, duration=540, distance=28)

    def try_login(self):
        try:
            username = validate_username(self.username_edit.text())
        except ValueError as exc:
            self.error_label.setText(str(exc))
            fade_in(self.error_label, 300)
            return
        password = self.password_edit.text()
        if models.verify_login(self.conn, username, password):
            self.username = username
            self.accept()
        else:
            self.error_label.setText("Invalid username or password.")
            fade_in(self.error_label, 300)
            shake(self)
            self.password_edit.clear()
            self.password_edit.setFocus()
