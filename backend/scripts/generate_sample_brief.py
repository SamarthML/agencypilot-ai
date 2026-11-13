"""Generate the 3-page Bloom Bakery client brief used to seed the Client Copilot.

All content is fictional. It is consistent with the demo marketing CSV (Bloom Bakery's Paid
Social push starting 18 Oct 2026, ~$32 average order value) so Copilot and Insights agree.
The output is deterministic (fixed creation date) so regenerating doesn't create a git diff.

Usage (from backend/):
    .\\.venv\\Scripts\\python.exe scripts/generate_sample_brief.py
"""

import argparse
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

logger = logging.getLogger("generate_sample_brief")

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT = BACKEND_DIR / "sample_data" / "bloom_bakery_brief.pdf"
CREATED = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
BRAND = (124, 58, 237)  # violet, the agency accent
BODY_SIZE = 10
LINE = 5.2

Block = tuple[str, str | Sequence[str] | Sequence[Sequence[str]]]

PAGE_1: list[Block] = [
    ("h2", "About Bloom Bakery"),
    (
        "p",
        "Bloom Bakery is an independent, family-owned bakery founded in 2017 by Maya and Luis "
        "Ortega. It runs three neighbourhood bakeries in Austin, Texas (East Austin, Mueller and "
        "South Lamar) plus online pre-orders with local delivery and in-store pickup. Best "
        "sellers are the sourdough loaves, cardamom morning buns, seasonal fruit galettes and "
        "custom celebration cakes. Average online order value is about $32.",
    ),
    ("h2", "Brand voice"),
    (
        "p",
        "Warm, neighbourly and quietly confident - like a friend who bakes really well. Playful "
        "but never silly. We talk about real ingredients, real people and the early mornings "
        'behind every loaf. Tagline: "Baked this morning, loved all day."',
    ),
    (
        "ul",
        [
            'Do: use sensory, specific language ("crackly crust", "still warm at 7am").',
            "Do: name our bakers and local farm partners; show the process, not stock photos.",
            "Do: write short sentences and use 'we' and 'you'.",
            'Don\'t: use discount-first language like "cheap", "deal of the century" or '
            "all-caps urgency.",
            'Don\'t: use the words "artisanal", "decadent" or "guilt-free".',
            "Emoji: at most one per social post, food-related only.",
        ],
    ),
    ("h2", "Target audience"),
    (
        "p",
        "Primary market: Austin households within a 6-mile radius of our three locations. Our "
        "customers are 60% women; the core age range is 25-44.",
    ),
    (
        "ul",
        [
            "Weekend Treaters (about 45% of revenue): 25-40, young professionals and couples who "
            "visit Saturday and Sunday mornings. Discover us on Instagram and TikTok; respond to "
            "new seasonal items and behind-the-scenes content.",
            "Office Orderers (about 25%): office managers and team leads ordering pastry boxes "
            "for meetings, mostly Tuesday to Thursday. Find us through Google search; value "
            "reliable delivery before 9am and easy invoicing.",
            "Celebration Planners (about 30%): 30-50, parents ordering birthday and holiday "
            "cakes 1-2 weeks ahead. Highest order value (around $65); reached through email and "
            "word of mouth.",
        ],
    ),
]

PAGE_2: list[Block] = [
    ("h2", "Q4 2026 goals (October - December)"),
    (
        "ul",
        [
            "Grow online pre-order revenue 25% versus Q4 2025 ($38,400), to $48,000.",
            "Sell 1,400 Thanksgiving pies and 900 holiday cookie boxes.",
            "Grow the email list from 6,500 to 9,000 subscribers by 31 December.",
            "Keep blended return on ad spend (ROAS) at or above 3.0 and cost per acquisition "
            "(CPA) at or below $14.",
            "Lift average order value from $32 to $36 with add-ons (coffee beans, gift cards).",
        ],
    ),
    ("h2", "Q4 budget: $18,000 total"),
    (
        "table",
        [
            ["Channel", "Budget", "Share", "Focus"],
            ["Paid Social (Meta, TikTok)", "$7,200", "40%", "Seasonal launches, retargeting"],
            ["Paid Search (Google)", "$5,400", "30%", "Office catering + holiday pre-orders"],
            ["Local partnerships", "$2,400", "13%", "Micro-influencers, farmers markets"],
            ["Email and CRM", "$1,800", "10%", "Pre-order reminders, list growth"],
            ["Creative production", "$1,200", "7%", "Photo and short video shoots"],
        ],
    ),
    (
        "p",
        "Budget changes over 10% between channels need sign-off from Maya Ortega (owner). "
        "Monthly reporting is due by the 5th of each month.",
    ),
    ("h2", "Key Q4 dates"),
    (
        "ul",
        [
            '18 October: "Pumpkin Season" Paid Social campaign launches.',
            "3 November: Thanksgiving pie pre-orders open; they close 24 November.",
            "1-22 December: holiday cookie boxes and gift cards.",
            "25-26 December: all bakeries closed.",
        ],
    ),
    ("h2", "Competitors"),
    (
        "ul",
        [
            "Crumb & Co: regional chain with 9 Austin locations. Prices about 20% lower and strong "
            "on delivery apps, but mass-produced. Our edge: freshness, local sourcing and "
            "custom cakes.",
            "Sugar Loaf Patisserie: premium French bakery downtown with 48,000 Instagram "
            "followers (we have 12,400). Higher prices; beautiful visuals. Our edge: warmer, "
            "neighbourhood feel and faster office delivery.",
            "Supermarket in-store bakeries: cheapest option for holiday pies. Our edge: quality "
            "and the pre-order experience; never compete on price.",
        ],
    ),
]

PAGE_3: list[Block] = [
    ("h2", "Past campaign results (2025-2026)"),
    (
        "table",
        [
            ["Campaign", "Dates", "Spend", "Revenue", "ROAS"],
            ["Holiday Pre-orders 2025", "Nov-Dec 2025", "$9,600", "$38,400", "4.0"],
            ["Valentine's Cake Drop", "Feb 2026", "$1,500", "$6,300", "4.2"],
            ["Spring Sourdough Launch", "Mar-Apr 2026", "$3,200", "$8,960", "2.8"],
            ["Mother's Day Brunch Boxes", "May 2026", "$2,100", "$10,500", "5.0"],
            ["Summer TikTok Test", "Jul 2026", "$1,800", "$2,700", "1.5"],
            ["Back-to-School Office Orders", "Sep 2026", "$2,400", "$7,920", "3.3"],
        ],
    ),
    ("h2", "What we learned"),
    (
        "ul",
        [
            "Pre-order campaigns win. Holiday 2025 and Mother's Day both beat a ROAS of 4.0 "
            "because customers commit early; reminder emails 48 hours before the cut-off drove "
            "31% of Holiday 2025 orders.",
            "Mother's Day Brunch Boxes was our best campaign ever (ROAS 5.0). The winning creative "
            "was a 15-second video of Luis boxing pastries at 6am.",
            "The Summer TikTok Test underperformed (ROAS 1.5). Trend-driven, jokey content felt "
            "off-brand; comments asked for more baking process. Do not repeat that format.",
            "Office orders respond to Google Search, not social: 78% of Back-to-School office "
            'orders came from search terms like "pastry delivery Austin".',
            "Discount codes over 15% attracted one-time buyers; only 9% ordered again.",
        ],
    ),
    ("h2", "Current status: Pumpkin Season (from 18 October 2026)"),
    (
        "p",
        "Early results are strong: Paid Social sessions are up about 60% since launch and the "
        "pumpkin cardamom bun is the top seller at all three locations. Next step: shift $600 "
        "from Paid Search to Paid Social retargeting for Thanksgiving pre-orders, pending Maya's "
        "approval.",
    ),
    ("h2", "Agency contacts"),
    (
        "p",
        "Account lead: Priya Shah. Paid media: Tom Becker. Content and social: Ana Ruiz. "
        "Client-side approver: Maya Ortega (owner).",
    ),
]


class BriefPdf(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*BRAND)
        self.cell(0, 6, "BLOOM BAKERY  |  CLIENT BRIEF 2026", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Confidential - prepared by the agency - page {self.page_no()} of 3")
        self.set_text_color(0, 0, 0)


def write_block(
    pdf: FPDF, kind: str, content: str | Sequence[str] | Sequence[Sequence[str]]
) -> None:
    if kind == "h2":
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, str(content), new_x="LMARGIN", new_y="NEXT")
    elif kind == "p":
        pdf.set_font("Helvetica", "", BODY_SIZE)
        pdf.multi_cell(0, LINE, str(content), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    elif kind == "ul":
        pdf.set_font("Helvetica", "", BODY_SIZE)
        for item in content:
            pdf.multi_cell(0, LINE, f"-  {item}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.8)
    elif kind == "table":
        write_table(pdf, content)  # type: ignore[arg-type]


def write_table(pdf: FPDF, rows: Sequence[Sequence[str]]) -> None:
    pdf.set_font("Helvetica", "", 9)
    heading = FontFace(emphasis="BOLD", fill_color=(237, 233, 254))
    with pdf.table(line_height=5.5, headings_style=heading, padding=1.2) as table:
        for row in rows:
            cells = table.row()
            for value in row:
                cells.cell(value)
    pdf.ln(2)


def build(out: Path) -> None:
    pdf = BriefPdf(format="A4")
    pdf.set_margins(18, 14, 18)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_title("Bloom Bakery - Client Brief 2026")
    pdf.set_author("AgencyPilot demo agency")
    pdf.set_creation_date(CREATED)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "Bloom Bakery - Client Brief", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0, 5, "Prepared October 2026 for the Q4 2026 campaign season", new_x="LMARGIN", new_y="NEXT"
    )
    for page_blocks in (PAGE_1, PAGE_2, PAGE_3):
        if page_blocks is not PAGE_1:
            pdf.add_page()
        for kind, content in page_blocks:
            write_block(pdf, kind, content)

    if pdf.page_no() != 3:
        raise RuntimeError(f"Brief should be exactly 3 pages, got {pdf.page_no()}")
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    logger.info("Wrote %s (%d pages)", out, pdf.page_no())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
