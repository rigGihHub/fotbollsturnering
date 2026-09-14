from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UI=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
AI=(ROOT/"cupnavi_core/ai_kit_suggestion.py").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_api/admin_repository.py").read_text(encoding="utf-8")
CSS=(ROOT/"frontend-next/src/app/admin-polish-v2629.css").read_text(encoding="utf-8")

def test_one_action_searches_every_team_with_bounded_parallelism():
    assert "searchAllTeamAssets" in UI
    assert "Sök för alla lag" in UI
    assert "start+=3" in UI
    assert "Osäkra träffar lämnades oförändrade" in UI

def test_logos_are_sourced_and_persisted():
    for field in ("logo_url","logo_source_url","logo_verified"):
        assert field in AI
    assert "logo_url" in REPO and "logo_source_url" in REPO
    assert "admin-team-logo" in UI

def test_team_color_uses_a_shirt_silhouette():
    assert "admin-team-shirt" in UI
    assert "clip-path:polygon" in CSS

def test_completed_steps_offer_forward_navigation():
    assert "Spara och fortsätt till Lag" in UI
    assert "Klar med lag → Grupper" in UI
    assert "Fortsätt till Planer & tider" in UI

def test_enabled_and_disabled_buttons_are_visually_distinct():
    assert "button:not(:disabled)" in CSS
    assert "button:disabled" in CSS
