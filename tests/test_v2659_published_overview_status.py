from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_published_cup_does_not_ask_for_pitch_review_again():
    source = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text()
    assert 'status:isPublished?"Godkända"' in source
    assert 'state:isPublished?"done"' in source
