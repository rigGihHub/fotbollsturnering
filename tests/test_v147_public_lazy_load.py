from pathlib import Path
from cupnavi_core.public_view import match_summary

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
PUBLIC=APP[APP.index("def render_public_view"):APP.index("def render_match_reporter_view")]

def test_public_groups_are_lazy_not_loaded_at_entry():
    head=PUBLIC[:PUBLIC.index("def _public_source_team_id")]
    assert "def _load_public_groups" in head
    assert "public_groups = all_rows" not in head
    assert 'lambda: all_rows("SELECT * FROM groups' in head

def test_matcher_only_metrics_live_inside_matcher_branch():
    before=PUBLIC[:PUBLIC.index('if public_page == "Matcher":')]
    assert "total_goals =" not in before
    assert "team_count = len(public_teams)" not in before
    matcher=PUBLIC[PUBLIC.index('if public_page == "Matcher":'):PUBLIC.index('if public_page == "Statistik":')]
    assert "total_goals =" in matcher
    assert "team_count = len(public_teams)" in matcher

def test_dead_visitor_rows_builder_removed():
    assert "visitor_rows = []" not in PUBLIC
    assert "visitor_rows.append" not in PUBLIC

def test_screen_stays_lazy_and_statistics_moved_out_of_main_public_renderer():
    assert "_screen_table_bundle = calculate_all_group_tables(tournament_id, tournament)" in PUBLIC
    assert 'screen_groups = _screen_table_bundle["groups"][:4]' in PUBLIC
    assert "render_public_statistics_section(" in PUBLIC
    assert "forecast_groups =" not in PUBLIC

def test_public_summary_helper():
    rows=[
        {"home_score":2,"away_score":1},
        {"home_score":None,"away_score":None},
    ]
    assert match_summary(rows)=={"total":2,"played":1,"goals":3}
