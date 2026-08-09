"""Shared UI helpers: notifications, tables, printing and form widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

# QtPrintSupport is not available in the Android builds, so it is imported
# lazily and the print/PDF helpers degrade gracefully when it is missing.
try:
    from PySide6.QtPrintSupport import QPrinter, QPrintDialog

    _HAS_PRINT = True
except Exception:  # noqa: BLE001
    QPrinter = QPrintDialog = None
    _HAS_PRINT = False

from utils.formatting import format_currency


def label(text="", size=13, bold=False, color=None, object_name=None):
    """Return a styled QLabel."""
    lbl = QLabel(text)
    font = QFont("Segoe UI", size)
    font.setBold(bold)
    lbl.setFont(font)
    if color:
        lbl.setStyleSheet(f"color: {color};")
    if object_name:
        lbl.setObjectName(object_name)
    return lbl


def page_header(text):
    lbl = QLabel(text)
    lbl.setObjectName("pageHeader")
    return lbl


def notify(parent, text, title="Notice", error=False):
    """Show a modal message box."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    if error:
        box.setIcon(QMessageBox.Icon.Critical)
    else:
        box.setIcon(QMessageBox.Icon.Information)
    box.exec()


def confirm(parent, text, title="Confirm") -> bool:
    """Ask yes/no and return the choice."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    yes = box.addButton("Yes", QMessageBox.ButtonRole.YesRole)
    box.addButton("No", QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(yes)
    box.exec()
    return box.clickedButton() is yes


def setup_table(table, headers, widths=None):
    """Configure a QTableWidget with headers, widths and read-only rows."""
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    if widths:
        for col, w in enumerate(widths):
            table.setColumnWidth(col, w)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    table.horizontalHeader().setStretchLastSection(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setSortingEnabled(False)


def clear_table(table):
    table.setRowCount(0)


def fill_table(table, rows, date_columns=(), time_columns=(), money_columns=()):
    """Populate a QTableWidget from a list of value tuples.

    ``money_columns`` indexes are rendered with Rs. formatting and right aligned.
    """
    table.setSortingEnabled(False)
    table.setRowCount(0)
    for r, row in enumerate(rows):
        table.insertRow(r)
        for c, value in enumerate(row):
            item = QTableWidgetItem()
            if c in money_columns:
                item.setText(format_currency(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            elif c in date_columns:
                item.setText(str(value))
            else:
                item.setText(str(value))
            table.setItem(r, c, item)
    return table


def make_button(text, obj_name="", on_click=None, tooltip=None):
    btn = QPushButton(text)
    if obj_name:
        btn.setObjectName(obj_name)
    if on_click:
        btn.clicked.connect(on_click)
    if tooltip:
        btn.setToolTip(tooltip)
    return btn


def hline():
    from PySide6.QtWidgets import QFrame

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #e3e8ef;")
    return line


def render_report_html(title, subtitle, headers, rows, total_row=None):
    """Build an HTML table suitable for printing / PDF export."""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = "".join(f"<td>{c}</td>" for c in row)
        body += f"<tr>{cells}</tr>"
    if total_row:
        cells = "".join(f"<td><b>{c}</b></td>" for c in total_row)
        body += f'<tr style="background:#dbe7ff;">{cells}</tr>'
    return f"""<html><head><meta charset="utf-8"><style>
    body {{ font-family: 'Segoe UI', sans-serif; font-size: 11pt; }}
    h2 {{ margin: 0; }} h3 {{ margin: 2px 0 12px 0; color: #666; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th {{ background: #1f2a3d; color: #fff; padding: 6px 8px; text-align: left; }}
    td {{ border: 1px solid #ccd6e2; padding: 4px 8px; }}
    </style></head><body>
    <h2>{title}</h2><h3>{subtitle}</h3>
    <table><tr>{head}</tr>{body}</table>
    </body></html>"""


def print_table(parent, title, subtitle, headers, rows, total_row=None):
    """Send a report to the printer via the standard print dialog."""
    if not _HAS_PRINT:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            parent, "Printing", "Printing is not available on this device."
        )
        return
    html = render_report_html(title, subtitle, headers, rows, total_row)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return
    doc = QTextBrowser()
    doc.setHtml(html)
    doc.print_(printer)


def export_report_pdf(parent, html, file_path):
    """Save an HTML report to a PDF using Qt's printing backend."""
    if not _HAS_PRINT:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            parent, "Export PDF", "PDF export is not available on this device."
        )
        return file_path
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(file_path)
    printer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.A4),
        QPageLayout.Orientation.Landscape,
        QMarginsF(10, 10, 10, 10),
        QPageLayout.Unit.Millimeter,
    ))
    document = QTextDocument()
    document.setHtml(html)
    document.print_(printer)
    return file_path


def form_row(fields: list, parent=None):
    """Build an HBox containing label:field pairs. Returns the box."""
    box = QHBoxLayout()
    for label_text, field in fields:
        lbl = label(label_text, size=12)
        lbl.setStyleSheet("color: #334155;")
        box.addWidget(lbl)
        box.addWidget(field)
    box.addStretch()
    return box
