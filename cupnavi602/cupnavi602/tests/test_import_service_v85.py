import pandas as pd
from cupnavi_core.import_service import (
    TEAM_FIELDS, PLAYER_FIELDS, auto_map_columns,
    build_team_import_plan, build_player_import_plan,
)

def test_auto_mapping_understands_swedish_and_english_headers():
    mapping = auto_map_columns(["Team Name", "Group", "Distance km"], TEAM_FIELDS)
    assert mapping["Lag"] == "Team Name"
    assert mapping["Grupp"] == "Group"
    assert mapping["Resväg km"] == "Distance km"

def test_team_plan_flags_duplicate_and_invalid_color():
    df = pd.DataFrame([
        {"Lag": "AIK", "Hemmafärg": "#000000"},
        {"Lag": "ÖSK", "Hemmafärg": "svart"},
    ])
    records, issues = build_team_import_plan(
        df, {"Lag":"Lag","Hemmafärg":"Hemmafärg"}, existing_names=["AIK"]
    )
    assert records == []
    assert any(x["Nivå"] == "Hoppa över" for x in issues)
    assert any(x["Nivå"] == "Fel" for x in issues)

def test_team_plan_enforces_remaining_capacity():
    df = pd.DataFrame([{"Lag":"A"},{"Lag":"B"}])
    records, issues = build_team_import_plan(df, {"Lag":"Lag"}, [], max_new_teams=1)
    assert len(records) == 2
    assert any("bara plats för 1" in x["Meddelande"] for x in issues)

def test_player_plan_requires_existing_team_and_skips_duplicate():
    df = pd.DataFrame([
        {"Lag":"ÖSK","Spelare":"Ada"},
        {"Lag":"Saknas","Spelare":"Bo"},
    ])
    records, issues = build_player_import_plan(
        df, {"Lag":"Lag","Spelare":"Spelare"}, {"ösk":7}, [(7,"Ada")]
    )
    assert records == []
    assert any(x["Nivå"] == "Hoppa över" for x in issues)
    assert any(x["Nivå"] == "Fel" for x in issues)
