"""Global stylesheet for a clean, modern admin UI."""

from __future__ import annotations

QSS = """
QWidget {
    font-family: 'Segoe UI', 'Microsoft Sans Serif';
    font-size: 13px;
    color: #2b2f36;
}
QMainWindow, QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eef2f8, stop:1 #e4ebf6);
}
#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #141d33, stop:1 #1e3052);
    min-width: 230px;
    max-width: 230px;
}
#sidebarTitle {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
    padding: 20px 16px 2px 16px;
    background: transparent;
}
#sidebarSubtitle {
    color: #94a8c8;
    font-size: 11px;
    padding: 0 16px 14px 16px;
    background: transparent;
}
QListWidget#navList {
    background: transparent;
    border: none;
    outline: 0;
    padding: 4px;
}
QListWidget#navList::item {
    color: #b7c6dd;
    padding: 11px 18px;
    border: none;
    border-radius: 9px;
    margin: 2px 8px;
}
QListWidget#navList::item:hover {
    background: #26375a;
    color: #ffffff;
}
QListWidget#navList::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
    color: #ffffff;
    border-left: 3px solid #93c5fd;
}
#content {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eef2f8, stop:1 #e3eaf5);
}
#pageHeader {
    font-size: 21px;
    font-weight: 700;
    color: #16233c;
}
#card {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255, 255, 255, 165), stop:1 rgba(255, 255, 255, 120));
    border: 1px solid rgba(255, 255, 255, 230);
    border-radius: 18px;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3f88fa, stop:1 #2b6df0);
}
QPushButton:pressed { background: #275bb8; }
QPushButton:disabled { background: #b6c3d6; color: #e8edf4; }
QPushButton#secondary {
    background: #eef2f8;
    color: #1f2a3d;
    border: 1px solid #d4dce8;
}
QPushButton#secondary:hover { background: #e2e9f4; }
QPushButton#danger {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ef4444, stop:1 #dc2626);
}
QPushButton#danger:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f25050, stop:1 #e04040);
}
QPushButton#success {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #16a34a);
}
QPushButton#success:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2bd06a, stop:1 #1bb454);
}

QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #d3dcea;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: #3b82f6;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #3b82f6;
    background: #fbfdff;
}
QLineEdit:read-only { background: #f0f3f7; }

QTableWidget, QTableView {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    gridline-color: #eef2f7;
    selection-background-color: #dbe7ff;
    selection-color: #16233c;
}
QTableWidget::item { padding: 6px; }
QTableWidget::item:hover { background: #f5f8fd; }
QHeaderView::section {
    background: #f1f5fb;
    border: none;
    border-bottom: 2px solid #dfe6f0;
    padding: 9px 8px;
    font-weight: 700;
    color: #33415c;
}

QGroupBox {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 12px;
    background: #ffffff;
    font-weight: 600;
    color: #16233c;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #c3ccdb; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #9fb0c6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c3ccdb; border-radius: 5px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QStatusBar { background: #1f2a3d; color: #c9d6e8; }
QStatusBar::item { border: none; }

QProgressBar {
    border: 1px solid #ccd6e2;
    border-radius: 5px;
    text-align: center;
    background: #ffffff;
}
QProgressBar::chunk { background: #3b82f6; border-radius: 4px; }

QLabel#statValue { font-size: 26px; font-weight: 700; }
QLabel#statLabel { font-size: 12px; color: #6b7280; }
QLabel#noteText { color: #64748b; font-size: 12px; }
QLabel#errorText { color: #dc2626; font-size: 12px; }

/* Decorative bits */
#heroBanner {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e3a8a, stop:1 #3b82f6);
    border-radius: 16px;
}
#pill {
    background: rgba(255, 255, 255, 0.16);
    border-radius: 12px;
}
#sectionAccent {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #93c5fd);
    border-radius: 2px;
}
"""
