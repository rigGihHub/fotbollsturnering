from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v431_group_proposal_is_explicit_preview():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "förhandsvisning – inget sparas förrän du väljer att använda det" in source
    assert 'Skapa {_recommended_groups} rekommenderade grupper",type="secondary"' in source


def test_v431_schedule_regeneration_requires_confirmation():
    source = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
    assert "Jag förstår att befintliga schematider kan ersättas" in source
    assert "Lagens gruppplacering, laguppgifter och sparade tävlingsregler ändras inte." in source
    assert "_regenerating_unplayed_schedule and not _confirm_regenerate" in source
