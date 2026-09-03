from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v394_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_matchcamp_recommendation_is_primary_and_actionable():
    assert "recommend_matchcamp_matches_per_team" in VIEW
    assert "Sätt {recommendation['matches_per_team']} matcher per lag" in VIEW
    assert "Hur många matcher ska varje lag få?" in VIEW


def test_tournament_recommendation_uses_same_decision_language():
    assert "**CupNavi rekommenderar:**" in VIEW
    assert "Använd CupNavis snabbförslag" in VIEW
