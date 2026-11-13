"""Helpers shared by the Insights CSV and Copilot document uploads."""

from pathlib import PurePath

# Matches the String(255) filename columns on insight_datasets and documents.
FILENAME_MAX_CHARS = 255
SUFFIX_MAX_CHARS = 16


def safe_filename(raw: str, default: str) -> str:
    """The client-supplied name reduced to something safe to store and display.

    Drops any client path (both separator styles, so `C:\\fakepath\\a.csv` and `../a.csv` become
    `a.csv`) and non-printable characters, and shortens long names to the column size while
    keeping the extension, which the Copilot uses to pick a parser.
    """
    base = PurePath(raw.replace("\\", "/")).name
    name = "".join(ch for ch in base if ch.isprintable()).strip()
    if not name:
        return default
    if len(name) <= FILENAME_MAX_CHARS:
        return name
    suffix = PurePath(name).suffix[:SUFFIX_MAX_CHARS]
    return name[: FILENAME_MAX_CHARS - len(suffix)] + suffix
