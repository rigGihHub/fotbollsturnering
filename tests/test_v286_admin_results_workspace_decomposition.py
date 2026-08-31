from pathlib import Path

import pandas as pd

from cupnavi_core.admin_results_view import prepare_admin_result_updates

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "admin_results_view.py").read_text(encoding="utf-8")
REPO = (ROOT / "cupnavi_core" / "admin_results_repository.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_and_module_boundary():
    assert VERSION == "2026.08.31-342-POST-SIMPLIFICATION-AUDIT"
    assert "render_admin_results_workspace(" in APP
    app_block = APP[APP.index('if admin_page == "Matcher och resultat":'):APP.index('if admin_page == "Matchhändelser":')]
    assert 'st.data_editor(' not in app_block
    assert 'SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage' not in app_block
    assert 'update_match_result_if_unchanged(' in app_block
    assert 'enqueue_goal_push_events(' in app_block


def test_view_owns_results_ui_and_repository_owns_read_queries():
    assert 'st.header("Resultat")' in VIEW
    assert 'st.data_editor(' in VIEW
    assert '"Visa hela matchschemat"' in VIEW
    assert '"bulk_result_conflict_message"' in VIEW
    assert 'fetch_admin_results_data(' in VIEW
    assert 'SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage' in REPO
    assert 'SELECT * FROM referees WHERE tournament_id=? ORDER BY name' in REPO
    assert 'SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name' in REPO


def test_prepare_updates_preserves_referee_only_change_and_snapshot():
    original = {
        "id": 7,
        "stage": "Gruppspel",
        "home_score": None,
        "away_score": None,
        "home_penalties": None,
        "away_penalties": None,
        "decided_winner_id": None,
        "referee_id": 1,
    }
    edited = pd.DataFrame([{
        "match_id": 7,
        "Fas": "Gruppspel",
        "Hemmalag": "A",
        "Hemmamål": None,
        "Bortamål": None,
        "Bortalag": "B",
        "Hemmastraffar": None,
        "Bortastraffar": None,
        "Avgörande vinnare": "–",
        "Domare": "Domare 2",
    }])
    updates, info, errors, by_id = prepare_admin_result_updates(
        edited,
        playable_matches=[original],
        referee_ids_by_name={"Domare 2": 2},
        result_team_id_by_name={"A": 10, "B": 11},
        playoff_tie_rule="Straffar",
    )
    assert not info and not errors
    assert len(updates) == 1
    assert updates[0]["referee_id"] == 2
    assert updates[0]["expected"]["referee_id"] == 1
    assert by_id[7] is original


def test_prepare_updates_keeps_partial_score_unsaved():
    original = {
        "id": 9,
        "stage": "Gruppspel",
        "home_score": None,
        "away_score": None,
        "home_penalties": None,
        "away_penalties": None,
        "decided_winner_id": None,
        "referee_id": None,
    }
    edited = pd.DataFrame([{
        "match_id": 9,
        "Fas": "Gruppspel",
        "Hemmalag": "A",
        "Hemmamål": 1,
        "Bortamål": None,
        "Bortalag": "B",
        "Hemmastraffar": None,
        "Bortastraffar": None,
        "Avgörande vinnare": "–",
        "Domare": "Ej tillsatt",
    }])
    updates, info, errors, _ = prepare_admin_result_updates(
        edited,
        playable_matches=[original],
        referee_ids_by_name={},
        result_team_id_by_name={"A": 10, "B": 11},
        playoff_tie_rule="Straffar",
    )
    assert updates == []
    assert errors == []
    assert info == ["A–B: fyll i båda målresultaten så sparas det automatiskt."]


def test_prepare_updates_rejects_tied_penalty_score():
    original = {
        "id": 10,
        "stage": "Final",
        "home_score": None,
        "away_score": None,
        "home_penalties": None,
        "away_penalties": None,
        "decided_winner_id": None,
        "referee_id": None,
    }
    edited = pd.DataFrame([{
        "match_id": 10,
        "Fas": "Final",
        "Hemmalag": "A",
        "Hemmamål": 1,
        "Bortamål": 1,
        "Bortalag": "B",
        "Hemmastraffar": 4,
        "Bortastraffar": 4,
        "Avgörande vinnare": "–",
        "Domare": "Ej tillsatt",
    }])
    updates, info, errors, _ = prepare_admin_result_updates(
        edited,
        playable_matches=[original],
        referee_ids_by_name={},
        result_team_id_by_name={"A": 10, "B": 11},
        playoff_tie_rule="Straffar",
    )
    assert updates == []
    assert info == []
    assert errors == ["A–B: fyll i ett komplett och avgörande straffresultat."]
