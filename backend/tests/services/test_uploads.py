"""safe_filename: what the Insights and Copilot uploads store as the file's name."""

import pytest

from app.services.uploads import FILENAME_MAX_CHARS, safe_filename


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("report.csv", "report.csv"),
        ("C:\\fakepath\\report.csv", "report.csv"),
        ("../../etc/passwd.csv", "passwd.csv"),
        ("  spaced name.pdf  ", "spaced name.pdf"),
        ("tab\there\x00.md", "tabhere.md"),
        ("", "fallback.csv"),
        ("dir/", "dir"),
        ("/", "fallback.csv"),
        ("\x07\x08", "fallback.csv"),
    ],
)
def test_safe_filename(raw: str, expected: str) -> None:
    assert safe_filename(raw, default="fallback.csv") == expected


def test_long_names_fit_the_column_and_keep_the_extension() -> None:
    name = safe_filename("q" * 400 + ".pdf", default="x")

    assert len(name) == FILENAME_MAX_CHARS
    assert name.endswith(".pdf")


def test_a_runaway_extension_cannot_crowd_out_the_name() -> None:
    name = safe_filename("a" * 300 + "." + "b" * 300, default="x")

    assert len(name) == FILENAME_MAX_CHARS
    assert name.startswith("a" * 200)
