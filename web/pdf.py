"""Server-side PDF report generation using ReportLab."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_report_pdf(
    title: str,
    subtitle: str,
    headers: list[str],
    rows: list[list],
    total_row: list | None = None,
    landscape_orient: bool = True,
) -> bytes:
    """Build a PDF report table and return the raw PDF bytes."""
    buf = BytesIO()
    page = landscape(A4) if landscape_orient else A4
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="Sales & Inventory Management System",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontSize=16, spaceAfter=2, leading=20
    )
    sub_style = ParagraphStyle(
        "ReportSub", parent=styles["Normal"], fontSize=10,
        textColor=colors.HexColor("#555555"), spaceAfter=10, leading=13,
    )
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=11)
    cell_bold = ParagraphStyle("CellBold", parent=cell_style, fontName="Helvetica-Bold")
    head_style = ParagraphStyle(
        "Head", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white,
    )

    data = [[Paragraph(str(h), head_style) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), cell_style) for c in r])
    if total_row:
        data.append([Paragraph(f"<b>{c}</b>", cell_bold) for c in total_row])

    table = Table(data, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2a3d")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccd6e2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5fb")]),
    ]
    if total_row:
        style.append(
            ("BACKGROUND", (0, len(data) - 1), (-1, len(data) - 1), colors.HexColor("#dbe7ff"))
        )
    table.setStyle(TableStyle(style))

    doc.build([
        Paragraph(title, title_style),
        Paragraph(subtitle, sub_style),
        Spacer(1, 2),
        table,
    ])
    return buf.getvalue()
