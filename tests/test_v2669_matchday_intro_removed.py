from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_matchday_starts_with_actionable_content():
    view = (ROOT / "frontend-next/src/components/PublicCupView.tsx").read_text()

    assert "Det viktigaste just nu" not in view
    assert "Nästa match, rätt plan och rätt tid" not in view
    assert ">CUPDAGEN<" not in view
    assert 'className="favorite-strip"' in view
    assert 'className="next-match-hero"' in view
