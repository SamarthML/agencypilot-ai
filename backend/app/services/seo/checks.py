"""Page extraction and the 10 rule-based SEO checks. Pure functions: HTML in, results out."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from app.schemas.seo import CheckStatus, SeoCheck

NON_VISIBLE_TAGS = ("script", "style", "noscript", "template", "svg", "head")
OG_REQUIRED = ("og:title", "og:description", "og:image")
TITLE_RANGE = (30, 60)
META_RANGE = (70, 160)
WORD_PASS, WORD_WARN = 300, 150
ALT_WARN_RATIO = 0.8

# id -> (name, weight). Weights sum to 100.
CHECKS: dict[str, tuple[str, int]] = {
    "title": ("Title tag", 15),
    "meta_description": ("Meta description", 12),
    "h1": ("Single H1", 12),
    "heading_hierarchy": ("Heading hierarchy", 6),
    "image_alt": ("Image alt text", 10),
    "canonical": ("Canonical link", 8),
    "viewport": ("Mobile viewport", 10),
    "https": ("HTTPS", 12),
    "open_graph": ("Open Graph tags", 7),
    "word_count": ("Content length", 8),
}


@dataclass(frozen=True)
class PageData:
    title: str | None = None
    meta_description: str | None = None
    h1s: list[str] = field(default_factory=list)
    heading_levels: list[int] = field(default_factory=list)
    images_total: int = 0
    images_with_alt: int = 0
    canonical: str | None = None
    viewport: str | None = None
    og: dict[str, str] = field(default_factory=dict)
    text: str = ""

    @property
    def word_count(self) -> int:
        return len(self.text.split())


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed or None


def _meta_content(soup: BeautifulSoup, attr: str, value: str) -> str | None:
    tag = soup.find("meta", attrs={attr: re.compile(f"^{re.escape(value)}$", re.I)})
    content = tag.get("content") if isinstance(tag, Tag) else None
    return _clean(content) if isinstance(content, str) else None


def _open_graph(soup: BeautifulSoup) -> dict[str, str]:
    tags: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        content = _clean(tag.get("content"))
        if isinstance(key, str) and key.lower().startswith("og:") and content:
            tags.setdefault(key.lower(), content)
    return tags


def _canonical(soup: BeautifulSoup) -> str | None:
    for link in soup.find_all("link", href=True):
        rel = link.get("rel") or []
        if "canonical" in [r.lower() for r in rel]:
            return _clean(link["href"])
    return None


def _visible_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(NON_VISIBLE_TAGS):
        tag.decompose()
    return _clean(soup.get_text(" ")) or ""


def extract_page(content: bytes | str, charset: str | None = None) -> PageData:
    """Parse HTML (bytes are decoded via the HTTP charset or the page's own <meta charset>)."""
    encoding = charset if isinstance(content, bytes) else None
    soup = BeautifulSoup(content, "html.parser", from_encoding=encoding)
    images = soup.find_all("img")
    title_tag = soup.find("title")
    return PageData(
        title=_clean(title_tag.get_text()) if title_tag else None,
        meta_description=_meta_content(soup, "name", "description"),
        h1s=[_clean(h.get_text()) or "" for h in soup.find_all("h1")],
        heading_levels=[int(h.name[1]) for h in soup.find_all(re.compile(r"^h[1-6]$"))],
        images_total=len(images),
        images_with_alt=sum(1 for img in images if img.has_attr("alt")),
        canonical=_canonical(soup),
        viewport=_meta_content(soup, "name", "viewport"),
        og=_open_graph(soup),
        text=_visible_text(soup),  # last: it removes non-visible tags from the soup
    )


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _result(check_id: str, status: CheckStatus, value: str, recommendation: str) -> SeoCheck:
    name, weight = CHECKS[check_id]
    return SeoCheck(
        id=check_id, name=name, status=status, value=value,
        recommendation=recommendation, weight=weight,
    )  # fmt: skip


def check_title(page: PageData, final_url: str) -> SeoCheck:
    low, high = TITLE_RANGE
    if not page.title:
        return _result(
            "title", "fail", "Missing", f"Add a unique <title> of {low}-{high} characters."
        )
    length = len(page.title)
    if low <= length <= high:
        return _result(
            "title", "pass", f"{length} characters", "Title length is in the ideal range."
        )
    advice = "Lengthen" if length < low else "Shorten (search results truncate it)"
    return _result(
        "title", "warn", f"{length} characters", f"{advice} the title to {low}-{high} characters."
    )


def check_meta_description(page: PageData, final_url: str) -> SeoCheck:
    low, high = META_RANGE
    if not page.meta_description:
        return _result(
            "meta_description", "fail", "Missing",
            f"Add a meta description of {low}-{high} characters that summarises the page.",
        )  # fmt: skip
    length = len(page.meta_description)
    if low <= length <= high:
        return _result(
            "meta_description", "pass", f"{length} characters", "Length is in the ideal range."
        )
    advice = "Expand" if length < low else "Trim"
    return _result(
        "meta_description", "warn", f"{length} characters",
        f"{advice} the meta description to {low}-{high} characters.",
    )  # fmt: skip


def check_h1(page: PageData, final_url: str) -> SeoCheck:
    count = len(page.h1s)
    if count == 1:
        return _result("h1", "pass", "1 H1 tag", "The page has exactly one main heading.")
    if count == 0:
        return _result("h1", "fail", "0 H1 tags", "Add one H1 that states the page's main topic.")
    return _result("h1", "warn", f"{count} H1 tags", "Keep a single H1; demote the others to H2.")


def check_heading_hierarchy(page: PageData, final_url: str) -> SeoCheck:
    levels = page.heading_levels
    if not levels:
        return _result(
            "heading_hierarchy", "fail", "No headings", "Structure the content with H1-H3 headings."
        )
    for previous, current in zip(levels, levels[1:], strict=False):
        if current > previous + 1:
            return _result(
                "heading_hierarchy", "warn", f"Skips H{previous} → H{current}",
                "Don't skip heading levels; nest H2 under H1, H3 under H2.",
            )  # fmt: skip
    return _result(
        "heading_hierarchy",
        "pass",
        f"{len(levels)} headings, no skipped levels",
        "Heading order is logical.",
    )


def check_image_alt(page: PageData, final_url: str) -> SeoCheck:
    total, with_alt = page.images_total, page.images_with_alt
    if total == 0:
        return _result("image_alt", "pass", "No images", "Nothing to fix.")
    value = f"{with_alt}/{total} images have alt text"
    if with_alt == total:
        return _result("image_alt", "pass", value, "Every image has an alt attribute.")
    status: CheckStatus = "warn" if with_alt / total >= ALT_WARN_RATIO else "fail"
    return _result(
        "image_alt",
        status,
        value,
        f"Add descriptive alt text to the {total - with_alt} image(s) without it.",
    )


def check_canonical(page: PageData, final_url: str) -> SeoCheck:
    if page.canonical:
        return _result("canonical", "pass", page.canonical, "A canonical URL is declared.")
    return _result(
        "canonical", "fail", "Missing",
        'Add <link rel="canonical"> pointing at the preferred URL to avoid duplicate content.',
    )  # fmt: skip


def check_viewport(page: PageData, final_url: str) -> SeoCheck:
    if not page.viewport:
        return _result(
            "viewport", "fail", "Missing",
            'Add <meta name="viewport" content="width=device-width, initial-scale=1">.',
        )  # fmt: skip
    if "width=device-width" in page.viewport.replace(" ", "").lower():
        return _result("viewport", "pass", page.viewport, "The page is set up for mobile screens.")
    return _result(
        "viewport", "warn", page.viewport, "Use width=device-width so the page scales on phones."
    )


def check_https(page: PageData, final_url: str) -> SeoCheck:
    if final_url.lower().startswith("https://"):
        return _result("https", "pass", "Served over HTTPS", "The page is served securely.")
    return _result(
        "https", "fail", "Served over HTTP", "Serve the page over HTTPS and redirect HTTP to it."
    )


def check_open_graph(page: PageData, final_url: str) -> SeoCheck:
    present = [tag for tag in OG_REQUIRED if tag in page.og]
    missing = [tag for tag in OG_REQUIRED if tag not in page.og]
    value = f"{len(present)}/{len(OG_REQUIRED)} required tags"
    if not missing:
        return _result(
            "open_graph", "pass", value, "Links to this page will preview well on social media."
        )
    status: CheckStatus = "warn" if present else "fail"
    return _result(
        "open_graph", status, value, f"Add {', '.join(missing)} for rich social previews."
    )


def check_word_count(page: PageData, final_url: str) -> SeoCheck:
    words = page.word_count
    value = f"{words:,} words"
    if words >= WORD_PASS:
        return _result("word_count", "pass", value, "The page has substantial content.")
    status: CheckStatus = "warn" if words >= WORD_WARN else "fail"
    return _result(
        "word_count", status, value, f"Expand the content to at least {WORD_PASS} useful words."
    )


ALL_CHECKS: tuple[Callable[[PageData, str], SeoCheck], ...] = (
    check_title,
    check_meta_description,
    check_h1,
    check_heading_hierarchy,
    check_image_alt,
    check_canonical,
    check_viewport,
    check_https,
    check_open_graph,
    check_word_count,
)


def run_checks(page: PageData, final_url: str) -> list[SeoCheck]:
    return [check(page, final_url) for check in ALL_CHECKS]
