
import sqlite3
from pathlib import Path

from cupnavi_core.experience import match_duration_minutes
from cupnavi_core.match_reporter_logic import prepare_bulk_result_update

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")


def _row(**overrides):
    row={
        "match_id":1,
        "Fas":"Gruppspel",
        "Hemmalag":"AIK",
        "Bortalag":"ÖSK",
        "Hemmamål":2,
        "Bortamål":1,
        "Hemmastraffar":None,
        "Bortastraffar":None,
        "Avgörande vinnare":"–",
    }
    row.update(overrides)
    return row


def _original(**overrides):
    row={
        "home_score":None,
        "away_score":None,
        "home_penalties":None,
        "away_penalties":None,
        "decided_winner_id":None,
        "referee_id":7,
    }
    row.update(overrides)
    return row


def _is_na(value):
    return value is None


def test_match_duration_accepts_sqlite_row_not_only_dict():
    con=sqlite3.connect(":memory:")
    con.row_factory=sqlite3.Row
    con.execute("CREATE TABLE rules(halves INTEGER,minutes_per_half INTEGER,halftime_minutes INTEGER)")
    con.execute("INSERT INTO rules VALUES(2,25,5)")
    row=con.execute("SELECT * FROM rules").fetchone()
    assert match_duration_minutes(row)==55


def test_match_duration_keeps_mapping_behavior():
    assert match_duration_minutes({"halves":2,"minutes_per_half":20,"halftime_minutes":5})==45


def test_group_result_preparation_clears_playoff_only_fields():
    prepared=prepare_bulk_result_update(
        _row(Hemmastraffar=5,Bortastraffar=4),
        _original(),
        team_id_by_name={"AIK":1,"ÖSK":2},
        playoff_tie_rule="Straffar",
        is_na=_is_na,
    )
    update=prepared["update"]
    assert update["home_score"]==2
    assert update["away_score"]==1
    assert update["home_penalties"] is None
    assert update["away_penalties"] is None
    assert update["expected"]["referee_id"]==7


def test_incomplete_score_is_guidance_not_database_update():
    prepared=prepare_bulk_result_update(
        _row(Hemmamål=2,Bortamål=None),
        _original(),
        team_id_by_name={"AIK":1,"ÖSK":2},
        playoff_tie_rule="Straffar",
        is_na=_is_na,
    )
    assert prepared["update"] is None
    assert "fyll i båda målresultaten" in prepared["info"][0]


def test_tied_playoff_requires_decisive_penalty_score():
    prepared=prepare_bulk_result_update(
        _row(Fas="Final",Hemmamål=1,Bortamål=1,Hemmastraffar=4,Bortastraffar=4),
        _original(),
        team_id_by_name={"AIK":1,"ÖSK":2},
        playoff_tie_rule="Straffar",
        is_na=_is_na,
    )
    assert prepared["update"] is None
    assert "avgörande straffresultat" in prepared["errors"][0]


def test_lottery_playoff_can_store_explicit_winner():
    prepared=prepare_bulk_result_update(
        _row(Fas="Final",Hemmamål=1,Bortamål=1,**{"Avgörande vinnare":"AIK"}),
        _original(),
        team_id_by_name={"AIK":1,"ÖSK":2},
        playoff_tie_rule="Lottning",
        is_na=_is_na,
    )
    assert prepared["update"]["decided_winner_id"]==1


def test_app_keeps_optimistic_lock_outside_pure_helper():
    assert "prepare_bulk_result_update(" in APP
    logic=(ROOT/"cupnavi_core/match_reporter_logic.py").read_text(encoding="utf-8")
    assert "update_match_result_if_unchanged" not in logic
    assert "update_match_result_if_unchanged(" in APP


def test_e2e_selects_test_environment_via_radio_control():
    assert 'get_by_role("radio",name="Testmiljö",exact=True)' in E2E
    assert "test_environment.check(force=True)" in E2E
    helper=E2E[E2E.index("def create_test_tournament_through_ui"):E2E.index("def representative_public_tokens")]
    assert 'get_by_text("Testmiljö",exact=True).click()' not in helper
