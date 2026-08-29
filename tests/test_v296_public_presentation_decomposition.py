from pathlib import Path

from cupnavi_core.public_presentation_view import public_match_events_html, public_rules_html

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_and_public_presentation_boundary():
    assert VERSION == "2026.08.29-299-PERSISTENT-PUBLIC-NAVIGATION"
    assert "from cupnavi_core.public_presentation_view import (" in APP
    for name in ("render_group_table", "render_bracket_tree", "public_match_events_html", "public_rules_html"):
        assert f"def {name}(" in PRESENTATION
    assert "def render_group_table(table_rows, tournament, group_id=None):" in APP
    assert "return _render_group_table_impl(" in APP
    assert "return _render_bracket_tree_impl(" in APP
    assert "return _public_match_events_html_impl(" in APP
    assert "return _public_rules_html_impl(" in APP


def test_presentation_module_does_not_own_database_connection_or_writes():
    assert "with db()" not in PRESENTATION
    assert ".commit(" not in PRESENTATION
    assert "UPDATE " not in PRESENTATION
    assert "INSERT INTO" not in PRESENTATION
    assert "DELETE FROM" not in PRESENTATION


def test_public_match_events_preserve_home_away_order_and_protected_name():
    match_row = {"home_source": "TEAM:1", "away_source": "TEAM:2"}
    rows = [
        {"player_name": "Away Scorer", "is_protected": 0, "team_id": 2, "team_name": "Away", "goals": 1, "red_cards": 0},
        {"player_name": "Secret", "is_protected": 1, "team_id": 1, "team_name": "Home", "goals": 2, "red_cards": 1},
    ]
    html = public_match_events_html(
        7,
        match_row=match_row,
        rows=rows,
        team_names={1: "Home", 2: "Away"},
        all_rows=lambda *_: [],
        one_row=lambda *_: None,
        row_value=lambda row, key, default=None: row.get(key, default),
        resolve_source=lambda source: int(source.split(":")[-1]),
        tr=lambda text: text,
    )
    assert html.index("Home") < html.index("Away")
    assert "Skyddad spelare" in html
    assert "Secret" not in html
    assert "×2" in html
    assert "🟥" in html


def test_public_rules_preserve_saved_tournament_semantics():
    tournament = {
        "sport": "Fotboll",
        "table_tiebreak": "Inbördes möten först",
        "playoff_format": "A- och B-slutspel",
        "playoff_tie_rule": "Förlängning + straffar",
        "extra_time_minutes": 5,
        "bronze_match": 1,
        "points_win": 3,
        "points_draw": 1,
        "points_loss": 0,
    }
    rules = {
        "halves": 2,
        "minutes_per_half": 15,
        "halftime_minutes": 3,
        "pitch_break_minutes": 5,
        "minimum_team_rest_minutes": 20,
        "avoid_consecutive_matches": 1,
        "consecutive_match_break_minutes": 10,
        "pitch_count": 4,
    }
    rendered = public_rules_html(
        tournament,
        rules,
        row_value=lambda row, key, default=None: row.get(key, default),
        sport_profile=lambda _sport: {"period_label": "halvlekar"},
    )
    assert "2 halvlekar × 15 minuter" in rendered
    assert "inbördes möten först" in rendered
    assert "5 minuters förlängning" in rendered
    assert "Bronsmatch spelas" in rendered
