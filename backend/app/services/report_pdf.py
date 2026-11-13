"""Server-side A4 PDF for a monthly report (fpdf2, core Helvetica font).

Core PDF fonts only cover Latin-1, so all text goes through `sanitize_pdf_text`, which maps
typographic characters LLMs like to emit (gpt-oss's 【】 citations, non-breaking hyphens, smart
quotes, arrows...) to plain equivalents instead of letting fpdf2 raise on them.
"""

import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.schemas.insights import ChannelBreakdown, Kpi, KpiUnit
from app.schemas.reports import Report
from app.services.analytics import format_value

Rgb = tuple[int, int, int]
Cell = tuple[str, Rgb]

BRAND: Rgb = (79, 70, 229)  # indigo-600, the app's brand-from
BRAND_LIGHT: Rgb = (238, 242, 255)
INK: Rgb = (24, 24, 27)  # zinc-900
MUTED: Rgb = (113, 113, 122)  # zinc-500
RULE: Rgb = (228, 228, 231)  # zinc-200
GOOD: Rgb = (21, 128, 61)
BAD: Rgb = (185, 28, 28)
MARGIN = 18
LINE = 5.4

_REPLACEMENTS = {
    "【": "[", "】": "]", "‘": "'", "’": "'", "‚": ",", "“": '"', "”": '"', "„": '"',
    "–": "-", "—": "-", "‐": "-", "‑": "-", "‒": "-", "−": "-", "…": "...", "•": "-",
    "→": "->", "←": "<-", "↑": "up", "↓": "down", "≈": "~", "≤": "<=", "≥": ">=", "×": "x",
    " ": " ", " ": " ", " ": " ", " ": " ", "​": "", "﻿": "",
    "✓": "v", "★": "*", "€": "EUR", "™": "(TM)",
}  # fmt: skip


def _latin1_char(char: str) -> str:
    try:
        char.encode("latin-1")
        return char
    except UnicodeEncodeError:
        ascii_form = unicodedata.normalize("NFKD", char).encode("ascii", "ignore").decode()
        return ascii_form or "?"


def sanitize_pdf_text(text: str) -> str:
    """Make `text` safe for fpdf2's Latin-1 core fonts without losing its meaning."""
    for source, target in _REPLACEMENTS.items():
        text = text.replace(source, target)
    return "".join(_latin1_char(char) for char in text)


def _change(kpi_delta: float | None) -> str:
    return "n/a" if kpi_delta is None else f"{kpi_delta:+.1f}%"


def _value(value: float | None, unit: KpiUnit) -> str:
    return "n/a" if value is None else format_value(value, unit)


def _change_color(kpi: Kpi) -> Rgb:
    if kpi.delta_pct is None or kpi.delta_pct == 0 or kpi.good_when == "neutral":
        return MUTED
    good = (kpi.delta_pct > 0) == (kpi.good_when == "up")
    return GOOD if good else BAD


class ReportPdf(FPDF):
    def __init__(self, report: Report) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report = report
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=20)
        self.set_title(sanitize_pdf_text(report.content.title))
        self.set_author("AgencyPilot AI")
        self.set_creation_date(datetime.now(UTC))

    def write_text(self, text: str, size: float = 10, style: str = "", color: Rgb = INK) -> None:
        self.set_font("Helvetica", style, size)
        self.set_text_color(*color)
        self.multi_cell(0, LINE, sanitize_pdf_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_draw_color(*RULE)
        self.line(MARGIN, self.get_y() - 2, self.w - MARGIN, self.get_y() - 2)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        r = self.report
        left = f"AgencyPilot AI  |  {r.client_name}  |  {r.month_label}  |  {r.meta.model}"
        self.cell(0, 5, sanitize_pdf_text(left), align="L")
        self.set_x(MARGIN)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="R")


def _cover(pdf: ReportPdf) -> None:
    r = pdf.report
    pdf.set_fill_color(*BRAND)
    pdf.rect(0, 0, pdf.w, 42, style="F")
    pdf.set_xy(MARGIN, 11)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(224, 231, 255)
    pdf.cell(
        0, 5, "AGENCYPILOT AI  |  MONTHLY PERFORMANCE REPORT", new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 11, sanitize_pdf_text(r.client_name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, sanitize_pdf_text(r.month_label), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_y(50)
    pdf.write_text(r.content.title, size=16, style="B")
    status = "Final" if r.status == "final" else "Draft"
    pdf.write_text(
        f"{status}  |  Compared with {r.metrics.period.previous_label}  |  "
        f"Prepared {r.updated_at:%d %b %Y}",
        size=9,
        color=MUTED,
    )
    pdf.ln(3)


def _heading(pdf: ReportPdf, title: str) -> None:
    if pdf.will_page_break(22):
        pdf.add_page()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*BRAND)
    pdf.cell(0, 7, sanitize_pdf_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*RULE)
    pdf.line(MARGIN, pdf.get_y(), pdf.w - MARGIN, pdf.get_y())
    pdf.ln(2.5)


def _bullets(pdf: ReportPdf, items: Sequence[str], numbered: bool = False) -> None:
    for index, item in enumerate(items, start=1):
        y = pdf.get_y()
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*BRAND)
        pdf.set_x(MARGIN)
        pdf.cell(7, LINE, f"{index}." if numbered else "-")
        pdf.set_xy(MARGIN + 7, y)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*INK)
        pdf.multi_cell(0, LINE, sanitize_pdf_text(item), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)


def _table(
    pdf: ReportPdf, header: Sequence[str], widths: Sequence[float], rows: list[list[Cell]]
) -> None:
    pdf.set_fill_color(*BRAND_LIGHT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*INK)
    for index, (label, width) in enumerate(zip(header, widths, strict=True)):
        pdf.cell(width, 7, label, fill=True, align="L" if index == 0 else "R")
    pdf.ln(7)
    pdf.set_draw_color(*RULE)
    pdf.set_font("Helvetica", "", 9)
    for row in rows:
        for index, ((text, color), width) in enumerate(zip(row, widths, strict=True)):
            pdf.set_text_color(*color)
            pdf.cell(
                width, 6.5, sanitize_pdf_text(text), border="B", align="L" if index == 0 else "R"
            )
        pdf.ln(6.5)
    pdf.ln(2)


def _kpi_table(pdf: ReportPdf) -> None:
    period = pdf.report.metrics.period
    rows: list[list[Cell]] = [
        [
            (k.label, INK),
            (_value(k.value, k.unit), INK),
            (_value(k.previous, k.unit), MUTED),
            (_change(k.delta_pct), _change_color(k)),
        ]
        for k in pdf.report.metrics.kpis
    ]
    header = ["Metric", period.label, period.previous_label, "Change"]
    _table(pdf, header, [66, 36, 36, 36], rows)


def _channel_rows(channels: Sequence[ChannelBreakdown]) -> list[list[Cell]]:
    rows: list[list[Cell]] = []
    for c in channels:
        delta = c.sessions_delta_pct
        color = MUTED if delta is None or delta == 0 else (GOOD if delta > 0 else BAD)
        rows.append(
            [
                (c.channel, INK),
                (f"{c.sessions:,}", INK),
                (_change(delta), color),
                (format_value(c.revenue, "currency"), INK),
                ("n/a" if c.roas is None else f"{c.roas:.2f}x", INK),
            ]
        )
    return rows


def _sections(pdf: ReportPdf) -> None:
    content = pdf.report.content
    _heading(pdf, "Executive summary")
    pdf.write_text(content.executive_summary)
    _heading(pdf, "Key metrics")
    _kpi_table(pdf)
    _heading(pdf, "Wins")
    _bullets(pdf, content.wins)
    _heading(pdf, "Challenges")
    _bullets(pdf, content.challenges)
    _heading(pdf, "Channel performance")
    pdf.write_text(content.channel_commentary)
    pdf.ln(2)
    header = ["Channel", "Sessions", "vs last month", "Revenue", "ROAS"]
    _table(pdf, header, [58, 29, 29, 29, 29], _channel_rows(pdf.report.metrics.channels))
    _seo_section(pdf)
    _heading(pdf, "Plan for next month")
    _bullets(pdf, content.next_month_plan, numbered=True)
    pdf.ln(3)
    pdf.write_text(content.closing_note, style="I", color=MUTED)


def _seo_section(pdf: ReportPdf) -> None:
    seo, text = pdf.report.metrics.seo, pdf.report.content.seo_highlights
    if seo is None or not text:
        return
    _heading(pdf, "SEO highlights")
    pdf.write_text(f"Site health score: {seo.score}/100  |  {seo.url}", size=9, color=MUTED)
    pdf.ln(1)
    pdf.write_text(text)
    if seo.top_issues:
        pdf.ln(1)
        _bullets(pdf, [f"{i.name}: {i.value}" for i in seo.top_issues])


def render(report: Report) -> bytes:
    pdf = ReportPdf(report)
    pdf.add_page()
    _cover(pdf)
    _sections(pdf)
    return bytes(pdf.output())
