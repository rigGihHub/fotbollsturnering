from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PITCH = (ROOT / "frontend-next" / "src" / "components" / "pitch-window-import-review.tsx").read_text(encoding="utf-8")
PLAYOFF = (ROOT / "frontend-next" / "src" / "components" / "playoff-import-review.tsx").read_text(encoding="utf-8")


def test_pitch_window_review_auto_opens_once_per_session():
    assert "cupnavi_pitch_window_review_seen_" in PITCH
    assert 'sessionStorage.setItem(key,"1")' in PITCH
    assert "setOpen(true)" in PITCH


def test_pitch_review_advances_import_chain_after_commit():
    assert 'cupnavi:import-review-next' in PITCH
    assert 'window.dispatchEvent(new Event(IMPORT_REVIEW_NEXT_EVENT))' in PITCH


def test_playoff_review_waits_until_pitch_windows_are_resolved():
    assert '/import/pitch-windows`' in PLAYOFF
    assert "pitchReview.available" in PLAYOFF
    assert "cupnavi_playoff_review_seen_" in PLAYOFF


def test_playoff_review_listens_for_next_import_step():
    assert 'window.addEventListener(IMPORT_REVIEW_NEXT_EVENT,advance)' in PLAYOFF
    assert "setReviewTick(value=>value+1)" in PLAYOFF
