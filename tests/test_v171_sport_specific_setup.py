from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.25-172-REQUESTS-SCORE-IMPACT"

def test_sport_setup_engine_exists():
    assert "def sport_setup_recommendation" in APP
    for sport_id in ("football","floorball","handball"):
        assert f'"{sport_id}":' in APP

def test_setup_can_apply_sport_defaults_safely():
    assert "Använd rekommenderade" in APP
    assert "apply_sport_defaults_" in APP
    assert "Sportprofilens standardvärden visas som referens" in APP
    assert "minimum_team_rest_minutes=?" in APP

def test_format_recommender_uses_same_sport_profile():
    assert 'preferred_group_sizes=tuple(sport_setup_recommendation(sport)["group_sizes"])' in APP

def test_top_nav_has_safe_brand_clearance():
    assert "padding-top:4.95rem !important;" in APP
    assert "width:min(100%, 225px);" in APP
    assert "cn-mode-nav-safezone" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
