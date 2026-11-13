"""Report narrative + PDF with the provider mocked: grounding, validation/retry, rendering."""

import re
from typing import cast

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.schemas.reports import ReportContent, ReportGenerateRequest
from app.services import llm, report_pdf, reports
from tests.fakes import FakeProvider, ok, use_provider
from tests.report_data import content, content_json, october_metrics, report

NO_DB = cast(Session, None)  # build_metrics and save_report are patched


def prompt_of(with_seo: bool = True) -> str:
    context = reports.build_report_context("Apex Fitness", october_metrics(with_seo))
    return "\n".join(m.content for m in reports.build_report_messages(context))


# --- Grounding --------------------------------------------------------------------------------


def test_prompt_carries_the_computed_metrics() -> None:
    prompt = prompt_of()

    assert '"this_month":4340.0' in prompt and '"previous_month":4500.0' in prompt
    assert '"change_pct":-3.6' in prompt
    assert '"channel":"Paid Search"' in prompt and '"channel":"Organic"' in prompt
    assert "Paid Search sessions up 24.0% vs September 2026 (1,500 → 1,860)" in prompt
    assert '"score_out_of_100":71' in prompt and "Canonical link (fail)" in prompt


def test_prompt_never_includes_daily_rows() -> None:
    prompt = prompt_of()

    assert re.findall(r"\d{4}-\d{2}-\d{2}", prompt) == []  # no per-day dates at all
    assert "timeseries" not in prompt and "by_channel" not in prompt


def test_prompt_without_audit_sends_null_seo() -> None:
    assert '"seo":null' in prompt_of(with_seo=False)


def test_system_prompt_forbids_invented_numbers() -> None:
    rules = reports.REPORT_SYSTEM_PROMPT
    assert "Every number you write must appear in the JSON" in rules
    assert "Never invent" in rules
    assert "if `seo` is null, return null" in rules


# --- Generation (validation + one retry) ------------------------------------------------------


@pytest.fixture
def saved(monkeypatch: pytest.MonkeyPatch) -> list[ReportContent]:
    """Patch the DB edges of generate_report and capture what would be saved."""
    captured: list[ReportContent] = []
    monkeypatch.setattr(
        reports, "build_metrics", lambda db, client, month: ("Apex Fitness", october_metrics())
    )

    def save(*args: object) -> None:
        body = args[4]
        assert isinstance(body, ReportContent)
        captured.append(body)

    monkeypatch.setattr(reports, "save_report", save)
    return captured


REQUEST = ReportGenerateRequest(client="apex-fitness", month="2026-10")


async def test_generate_validates_and_logs_report_feature(
    monkeypatch: pytest.MonkeyPatch, saved: list[ReportContent], usage_rows: list[llm.UsageRecord]
) -> None:
    fake = use_provider(monkeypatch, FakeProvider([ok(content_json())]))

    await reports.generate_report(NO_DB, REQUEST, "groq")

    assert saved[0].title.startswith("October 2026")
    assert [r.feature for r in usage_rows] == ["report"]
    assert fake.requests[0].json_schema is not None
    assert "4340.0" in fake.requests[0].messages[0].content


async def test_invalid_json_is_repaired_once(
    monkeypatch: pytest.MonkeyPatch, saved: list[ReportContent], usage_rows: list[llm.UsageRecord]
) -> None:
    too_few_plan_items = content_json().replace(
        '"next_month_plan":["Fix the canonical link.","Refresh organic content.","Hold spend."]',
        '"next_month_plan":["Only one."]',
    )
    fake = use_provider(monkeypatch, FakeProvider([ok(too_few_plan_items), ok(content_json())]))

    await reports.generate_report(NO_DB, REQUEST, "groq")

    assert len(fake.requests) == 2 and len(saved) == 1
    assert len(usage_rows) == 2


async def test_invalid_twice_raises(
    monkeypatch: pytest.MonkeyPatch, saved: list[ReportContent], usage_rows: list[llm.UsageRecord]
) -> None:
    use_provider(monkeypatch, FakeProvider([ok("not json"), ok('{"title": "x"}')]))

    with pytest.raises(llm.LLMOutputError):
        await reports.generate_report(NO_DB, REQUEST, "groq")
    assert saved == []


async def test_seo_highlights_dropped_when_there_is_no_audit(
    monkeypatch: pytest.MonkeyPatch, saved: list[ReportContent], usage_rows: list[llm.UsageRecord]
) -> None:
    monkeypatch.setattr(
        reports, "build_metrics", lambda db, c, m: ("Apex Fitness", october_metrics(False))
    )
    use_provider(monkeypatch, FakeProvider([ok(content_json("Invented SEO text."))]))

    await reports.generate_report(NO_DB, REQUEST, "groq")

    assert saved[0].seo_highlights is None


def test_content_schema_enforces_section_counts() -> None:
    body = content().model_dump()
    with pytest.raises(ValidationError):
        ReportContent.model_validate({**body, "next_month_plan": ["a", "b"]})
    with pytest.raises(ValidationError):
        ReportContent.model_validate({**body, "wins": ["only one"]})
    with pytest.raises(ValidationError):
        ReportContent.model_validate({**body, "title": ""})


# --- PDF --------------------------------------------------------------------------------------


def test_sanitize_maps_llm_typography_to_latin1() -> None:
    text = "【brief.pdf p.2】 — “ROAS” ≈ 5.5x → up; 12‑month ‘plan’… café"

    clean = report_pdf.sanitize_pdf_text(text)

    assert clean == "[brief.pdf p.2] - \"ROAS\" ~ 5.5x -> up; 12-month 'plan'... café"
    clean.encode("latin-1")  # never raises


def test_sanitize_degrades_unknown_characters() -> None:
    assert report_pdf.sanitize_pdf_text("ﬁne 🚀") == "fine ?"


@pytest.mark.parametrize("with_seo", [True, False])
def test_render_returns_a_pdf(with_seo: bool) -> None:
    pdf = report_pdf.render(report(with_seo))

    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    assert len(pdf) > 2000


def test_render_survives_unicode_heavy_text() -> None:
    body = content().model_copy(update={"executive_summary": "【a p.1】 ≈ → ‑ “x” 🚀 ✓ ★ 中文"})
    unicode_report = report().model_copy(update={"content": body})

    assert report_pdf.render(unicode_report).startswith(b"%PDF-")
