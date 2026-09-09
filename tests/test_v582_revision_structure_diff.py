from pathlib import Path
from cupnavi_core.revision_import import compare_revision_structure

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VER = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v582_version_and_review_only_structure_ui():
    assert "582-REVISION-STRUCTURE-DIFF" in VER
    assert "🧩 Strukturella ändringar" in APP
    assert "Jämförelsen ändrar ingenting i cupen" in APP
    assert "Granska lag" in APP and "Granska grupper" in APP and "Granska schema" in APP


def test_team_add_remove_and_group_move_are_detected():
    current = [
        {"name": "ÖSK P2014 Svart", "group_name": "Grupp A"},
        {"name": "Karlslunds IF", "group_name": "Grupp A"},
    ]
    payload = {"teams": [
        {"name": "ÖSK P2014 Svart", "group_name": "Grupp B"},
        {"name": "Adolfsbergs IK", "group_name": "Grupp A"},
    ]}
    diff = compare_revision_structure(current, [], payload)
    assert diff["added_teams"] == ["Adolfsbergs IK"]
    assert diff["removed_teams"] == ["Karlslunds IF"]
    assert diff["group_moves"] == [{"team": "ÖSK P2014 Svart", "from": "Grupp A", "to": "Grupp B"}]


def test_match_time_and_pitch_change_is_not_reported_as_remove_plus_add():
    current_matches = [{
        "phase": "group", "home": "ÖSK", "away": "AIK", "group": "Grupp A",
        "time": "2026-09-12T09:00", "venue": "Plan 1",
    }]
    payload = {"matches": [{
        "home_team": "ÖSK", "away_team": "AIK", "group_name": "Grupp A",
        "time": "09:30", "venue": "Plan 2", "stage": "Gruppspel", "duration": None,
    }]}
    diff = compare_revision_structure([], current_matches, payload)
    assert diff["counts"]["matches_changed"] == 1
    assert diff["counts"]["matches_added"] == 0
    assert diff["counts"]["matches_removed"] == 0
    assert diff["changed_matches"][0]["changes"] == ["tid 09:00 → 09:30", "plan Plan 1 → Plan 2"]


def test_added_and_removed_fixtures_are_detected_conservatively():
    current_matches = [{"phase":"group","home":"A","away":"B","group":"Grupp A","time":"09:00","venue":"Plan 1"}]
    payload = {"matches": [{"home_team":"A","away_team":"C","group_name":"Grupp A","time":"09:00","venue":"Plan 1","stage":"Gruppspel","duration":None}]}
    diff = compare_revision_structure([], current_matches, payload)
    assert diff["counts"]["matches_added"] == 1
    assert diff["counts"]["matches_removed"] == 1


def test_colour_and_squad_suffixes_are_not_stripped_from_team_identity():
    current = [{"name":"ÖSK P2014 Svart","group_name":"A"}]
    payload = {"teams":[{"name":"ÖSK P2014 Blå","group_name":"A"}]}
    diff = compare_revision_structure(current, [], payload)
    assert diff["counts"]["teams_added"] == 1
    assert diff["counts"]["teams_removed"] == 1
