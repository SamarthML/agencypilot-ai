"""Every SEO check against saved HTML fixtures (good/bad page) plus small inline snippets."""

from pathlib import Path

import pytest

from app.services.seo import checks
from app.services.seo.checks import PageData

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "seo"
HTTPS_URL = "https://apexfitness.example/classes"
HTTP_URL = "http://apexfitness.example/classes"


def load(name: str) -> PageData:
    return checks.extract_page((FIXTURES / name).read_bytes())


def html(head: str = "", body: str = "") -> PageData:
    return checks.extract_page(f"<html><head>{head}</head><body>{body}</body></html>")


def status_of(results: list[checks.SeoCheck], check_id: str) -> str:
    return next(r.status for r in results if r.id == check_id)


# --- Fixtures ------------------------------------------------------------------


def test_good_page_passes_every_check() -> None:
    results = checks.run_checks(load("good.html"), HTTPS_URL)

    assert [r.status for r in results] == ["pass"] * 10


def test_bad_page_fails_or_warns_everywhere() -> None:
    results = {r.id: r.status for r in checks.run_checks(load("bad.html"), HTTP_URL)}

    assert results == {
        "title": "fail",
        "meta_description": "fail",
        "h1": "fail",
        "heading_hierarchy": "warn",  # H2 -> H4
        "image_alt": "fail",
        "canonical": "fail",
        "viewport": "fail",
        "https": "fail",
        "open_graph": "fail",
        "word_count": "fail",
    }


def test_extraction_ignores_scripts_and_styles() -> None:
    page = load("good.html")

    assert "analytics" not in page.text and "font-family" not in page.text
    assert page.title == "Apex Fitness | Strength Classes in Austin, Texas"
    assert page.h1s == ["Strength classes that fit your week"]
    assert page.heading_levels == [1, 2, 3, 2, 3]
    assert (page.images_total, page.images_with_alt) == (2, 2)  # alt="" counts (decorative)
    assert page.canonical == "https://apexfitness.example/classes"


def test_every_result_carries_name_weight_and_advice() -> None:
    results = checks.run_checks(load("bad.html"), HTTP_URL)

    assert sum(r.weight for r in results) == 100
    assert all(r.name and r.value and r.recommendation for r in results)


# --- One check at a time ----------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "expected"),
    [("A" * 30, "pass"), ("A" * 60, "pass"), ("A" * 29, "warn"), ("A" * 61, "warn"), ("", "fail")],
)
def test_title_length(title: str, expected: str) -> None:
    page = html(head=f"<title>{title}</title>" if title else "")

    assert checks.check_title(page, HTTPS_URL).status == expected


@pytest.mark.parametrize(
    ("length", "expected"), [(70, "pass"), (160, "pass"), (69, "warn"), (161, "warn"), (0, "fail")]
)
def test_meta_description_length(length: int, expected: str) -> None:
    head = f'<meta name="Description" content="{"x" * length}">' if length else ""

    assert checks.check_meta_description(html(head=head), HTTPS_URL).status == expected


@pytest.mark.parametrize(("count", "expected"), [(1, "pass"), (2, "warn"), (0, "fail")])
def test_single_h1(count: int, expected: str) -> None:
    page = html(body="<h1>Heading</h1>" * count)

    result = checks.check_h1(page, HTTPS_URL)

    assert result.status == expected
    assert result.value == f"{count} H1 tag{'' if count == 1 else 's'}"


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("<h1>a</h1><h2>b</h2><h3>c</h3><h2>d</h2>", "pass"),
        ("<h1>a</h1><h3>skipped h2</h3>", "warn"),
        ("<p>no headings</p>", "fail"),
    ],
)
def test_heading_hierarchy(body: str, expected: str) -> None:
    assert checks.check_heading_hierarchy(html(body=body), HTTPS_URL).status == expected


@pytest.mark.parametrize(
    ("with_alt", "without_alt", "expected"),
    [(0, 0, "pass"), (5, 0, "pass"), (4, 1, "warn"), (3, 1, "fail"), (0, 2, "fail")],
)
def test_image_alt(with_alt: int, without_alt: int, expected: str) -> None:
    body = '<img src="a.png" alt="x">' * with_alt + '<img src="b.png">' * without_alt

    assert checks.check_image_alt(html(body=body), HTTPS_URL).status == expected


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        ('<link rel="canonical" href="https://x.example/">', "pass"),
        ('<link rel="Canonical alternate" href="https://x.example/">', "pass"),
        ('<link rel="alternate" href="https://x.example/fr">', "fail"),
    ],
)
def test_canonical(head: str, expected: str) -> None:
    assert checks.check_canonical(html(head=head), HTTPS_URL).status == expected


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        ('<meta name="viewport" content="width = device-width, initial-scale=1">', "pass"),
        ('<meta name="viewport" content="width=1024">', "warn"),
        ("", "fail"),
    ],
)
def test_viewport(head: str, expected: str) -> None:
    assert checks.check_viewport(html(head=head), HTTPS_URL).status == expected


def test_https_uses_the_final_url() -> None:
    page = html()

    assert checks.check_https(page, HTTPS_URL).status == "pass"
    assert checks.check_https(page, HTTP_URL).status == "fail"


@pytest.mark.parametrize(
    ("tags", "expected"),
    [(("og:title", "og:description", "og:image"), "pass"), (("og:title",), "warn"), ((), "fail")],
)
def test_open_graph(tags: tuple[str, ...], expected: str) -> None:
    head = "".join(f'<meta property="{t}" content="value">' for t in tags)

    result = checks.check_open_graph(html(head=head), HTTPS_URL)

    assert result.status == expected
    assert result.value == f"{len(tags)}/3 required tags"


@pytest.mark.parametrize(("words", "expected"), [(300, "pass"), (150, "warn"), (149, "fail")])
def test_word_count(words: int, expected: str) -> None:
    page = html(body=f"<p>{'word ' * words}</p>", head=f"<script>{'hidden ' * 500}</script>")

    assert checks.check_word_count(page, HTTPS_URL).status == expected


def test_charset_from_http_header_is_used() -> None:
    content = "<html><head><title>Café crème — menu</title></head></html>".encode(
        "latin-1", "replace"
    )

    assert checks.extract_page(content, "iso-8859-1").title == "Café crème ? menu"
