"""Tests for report PDF export (regression: QPageLayout.Margins crash)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication

from ui.widgets import export_report_pdf, render_report_html


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def html():
    return render_report_html(
        "Daily Sales Report",
        "08-08-2026",
        ["Product", "Unit Price", "Quantity", "Total"],
        [("Samsung S24", "Rs. 180,000", 2, "Rs. 360,000")],
        ["TOTAL", "", 2, "Rs. 360,000"],
    )


def test_export_report_pdf(qapp, html, tmp_path):
    path = str(tmp_path / "report.pdf")
    export_report_pdf(None, html, path)
    assert os.path.exists(path)
    assert os.path.getsize(path) > 0
    with open(path, "rb") as fh:
        assert fh.read(5) == b"%PDF-"
