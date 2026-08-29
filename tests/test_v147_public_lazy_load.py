from pathlib import Path
from cupnavi_core.public_view import match_summary

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
PUBLIC=APP[APP.index("def render_public_view"):APP.index("def render_match_reporter_view")]
SCREEN=(ROOT/"cupnavi_core"/"public_shell_view.py").read_text(encoding="utf-8")
MATCHES=(ROOT/"cupnavi_core"/"public_matches_view.py").read_text(encoding="utf-8")

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
    assert "render_public_matches_fragment_module(" in matcher
    assert "total_goals =" in MATCHES
    assert "team_count = len(public_teams)" in MATCHES

def test_dead_visitor_rows_builder_removed():
    assert "visitor_rows = []" not in PUBLIC
    assert "visitor_rows.append" not in PUBLIC

def test_screen_stays_lazy_and_statistics_moved_out_of_main_public_renderer():
    assert "render_public_screen_mode(" in PUBLIC
    assert "table_bundle = calculate_all_group_tables(tournament_id, tournament)" in SCREEN
    assert 'screen_groups = table_bundle["groups"][:4]' in SCREEN
    assert "render_public_statistics_section(" in PUBLIC
    assert "forecast_groups =" not in PUBLIC

def test_public_summary_helper():
    rows=[
        {"home_score":2,"away_score":1},
        {"home_score":None,"away_score":None},
    ]
    assert match_summary(rows)=={"total":2,"played":1,"goals":3}
