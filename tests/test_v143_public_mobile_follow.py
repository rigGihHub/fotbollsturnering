from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
PUBLIC_NAV = (ROOT / "cupnavi_core" / "public_navigation_view.py").read_text(encoding="utf-8")
PUBLIC_TEAM_FOLLOW = (ROOT / "cupnavi_core" / "public_team_follow.py").read_text(encoding="utf-8")
PUBLIC_TEAM_VIEW = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")

def test_follow_my_team_has_personal_dashboard():
    assert "⭐ Mitt lag" in PUBLIC_TEAM_FOLLOW
    assert "Nästa match" in PUBLIC_TEAM_FOLLOW
    assert "Visa mitt lags matcher" in PUBLIC_TEAM_VIEW
    assert "Bokmärk sidan" in PUBLIC_TEAM_VIEW

def test_followed_team_is_preserved_in_mobile_navigation():
    assert 'team_query = f"&team={int(requested_team_id)}"' in PUBLIC_NAV
    assert 'requested_team_id=requested_team_id' in APP
    assert "public_force_team_filter_" in PUBLIC_TEAM_VIEW

def test_favorite_match_datetime_is_defensive():
    assert "def match_datetime" in PUBLIC_TEAM_FOLLOW
    assert "except (TypeError, ValueError)" in PUBLIC_TEAM_FOLLOW
    assert "match_datetime(match, row_value) is not None" in PUBLIC_TEAM_FOLLOW

def test_public_follow_has_mobile_specific_css():
    assert "@media(max-width:760px)" in APP
    assert ".cn-follow-shell" in APP
    assert ".cn-next-card" in APP
