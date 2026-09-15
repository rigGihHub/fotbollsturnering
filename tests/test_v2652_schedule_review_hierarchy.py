from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = (ROOT / "frontend-next/src/components/schedule-admin.tsx").read_text(encoding="utf-8")
PITCH_REVIEW = (ROOT / "frontend-next/src/components/pitch-window-import-review.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend-next/src/app/schedule-clarity-v2652.css").read_text(encoding="utf-8")


def test_complete_schedule_is_presented_as_a_review_task():
    assert '"Granska matchschemat"' in SCHEDULE
    assert "Godkänn schemat" in SCHEDULE
    assert "Fortsätt till publicering" in SCHEDULE
    assert "Kontrollera avspark och plan" in SCHEDULE


def test_pending_pitch_windows_explain_why_review_is_required():
    assert "GÖR DETTA FÖRST" in PITCH_REVIEW
    assert "Bekräfta när planerna är öppna" in PITCH_REVIEW
    assert "om matcherna ryms på respektive plan" in PITCH_REVIEW


def test_match_metadata_and_filters_have_dedicated_structure():
    assert 'className="schedule-match-identity"' in SCHEDULE
    assert 'className="schedule-match-meta"' in SCHEDULE
    assert 'className="schedule-list-head"' in SCHEDULE
    assert "grid-template-columns:minmax(330px,1.15fr)" in CSS


def test_schedule_stats_are_three_equal_columns():
    assert ".schedule-stats{grid-template-columns:repeat(3,minmax(0,1fr))" in CSS
