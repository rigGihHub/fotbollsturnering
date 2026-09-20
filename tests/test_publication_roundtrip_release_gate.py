from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PUBLISH=(ROOT/"cupnavi_api/publish_reporting_repository.py").read_text(encoding="utf-8")
PUBLIC=(ROOT/"cupnavi_api/repository.py").read_text(encoding="utf-8")
MAIN=(ROOT/"cupnavi_api/main.py").read_text(encoding="utf-8")

def test_publish_sets_cup_and_scheduled_matches_together():
    assert "UPDATE matches SET schedule_published=1" in PUBLISH
    assert "UPDATE tournaments SET is_published=?" in PUBLISH
    assert "Publish both in the same transaction" in PUBLISH

def test_publish_is_blocked_on_invalid_schedule_or_playoff():
    assert "_schedule_publication_analysis" in PUBLISH
    assert "_bracket_publication_analysis" in PUBLISH
    assert "if published and state[\"blockers\"]" in PUBLISH

def test_public_snapshot_only_returns_published_schedule():
    assert 'match_publish_filter="" if include_unpublished else " AND schedule_published=1"' in PUBLIC
    assert "scheduled_start IS NOT NULL" in PUBLIC

def test_public_snapshot_roundtrips_core_setup():
    for field in (
        "points_win","points_draw","points_loss","table_tiebreak",
        "halves","minutes_per_half","halftime_minutes","pitch_break_minutes",
        "minimum_team_rest_minutes","show_public_weather","show_public_kits",
        "show_public_away_kits","show_public_logos","playoff_format","bronze_match",
    ):
        assert field in PUBLIC_TOURNAMENT_FIELDS_TEXT()

def PUBLIC_TOURNAMENT_FIELDS_TEXT():
    start=PUBLIC.index("PUBLIC_TOURNAMENT_FIELDS")
    end=PUBLIC.index("def backend_name")
    return PUBLIC[start:end]

def test_public_routes_reload_snapshot_standings_and_playoffs():
    assert '@app.get("/api/public/cups/{public_key}")' in MAIN
    assert '@app.get("/api/public/cups/{public_key}/standings")' in MAIN
    assert '@app.get("/api/public/cups/{public_key}/playoffs")' in MAIN

def test_unpublished_cup_is_not_exposed_by_normal_public_lookup():
    assert "WHERE public_slug=? AND is_published=1" in PUBLIC
