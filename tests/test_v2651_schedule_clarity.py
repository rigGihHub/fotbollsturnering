from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "frontend-next/src/components/schedule-admin.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend-next/src/app/schedule-clarity-v2651.css").read_text(encoding="utf-8")


def test_completed_schedule_leads_to_publication_instead_of_regeneration():
    assert "data.unscheduled_count>0&&<section" in VIEW
    assert "SCHEMAT ÄR KOMPLETT" in VIEW
    assert 'href="#publish"' in VIEW


def test_locked_matches_render_as_facts_instead_of_disabled_form_fields():
    assert 'match.played||match.schedule_locked?<div className="schedule-match-facts"' in VIEW
    assert "readableKickoff" in VIEW
    assert "schedule-match-row is-readonly" in VIEW


def test_schedule_desktop_and_mobile_rows_have_explicit_layouts():
    assert ".schedule-match-row.is-readonly" in CSS
    assert "grid-template-columns:minmax(240px,1.35fr)" in CSS
    assert "@media(max-width:760px)" in CSS


def test_filter_selection_is_not_misrepresented_as_disabled():
    assert 'aria-pressed={filter==="all"}' in VIEW
    assert 'disabled={filter==="all"}' not in VIEW
    assert ".schedule-filters button.is-active" in CSS
