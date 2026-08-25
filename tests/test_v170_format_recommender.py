from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.25-177-ADMIN-OVERVIEW-CLASS-PROGRESS"

def test_recommender_is_explainable_and_capacity_aware():
    assert "def recommend_tournament_format" in APP
    assert "preferred_group_sizes" in APP
    assert "capacity_matches" in APP
    assert "playoff_format_label" in APP

def test_setup_recommendation_requires_explicit_acceptance():
    assert "### 3. Rekommenderat tävlingsformat" in APP
    assert "Inget ändras förrän du accepterar" in APP
    assert "Använd rekommenderat format" in APP

def test_recommendation_uses_setup_dimensions():
    for token in ("team_count=_rec_team_count","pitch_count=_rec_pitch_count","available_minutes=_rec_available_minutes","match_minutes=_rec_match_minutes"):
        assert token in APP

def test_groups_can_be_created_from_accepted_recommendation():
    assert "Skapa {_recommended_groups} rekommenderade grupper" in APP
    assert "recommended_group_count" in APP

def test_admin_can_review_saved_recommendation():
    assert "CupNavi formatrekommendation" in APP
    assert "Det här är beslutsstöd." in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
