from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_follow_my_team_has_personal_dashboard():
    assert "⭐ Mitt lag" in APP
    assert "Nästa match" in APP
    assert "Visa mitt lags matcher" in APP
    assert "Bokmärk sidan" in APP

def test_followed_team_is_preserved_in_mobile_navigation():
    assert 'team_query = "&team=" + str(requested_team_id) if requested_team_id else ""' in APP
    assert "public_force_team_filter_" in APP

def test_favorite_match_datetime_is_defensive():
    block = APP[APP.index("def _public_match_dt"):APP.index("notification_rows =", APP.index("def _public_match_dt"))]
    assert "except (TypeError, ValueError)" in block
    assert "_public_match_dt(m) is not None" in block

def test_public_follow_has_mobile_specific_css():
    assert "@media(max-width:760px)" in APP
    assert ".cn-follow-shell" in APP
    assert ".cn-next-card" in APP
