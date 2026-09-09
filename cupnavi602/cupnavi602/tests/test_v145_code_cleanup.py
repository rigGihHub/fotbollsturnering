from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_confirmed_dead_helpers_removed():
    for name in ("save_tournament_day_window","centered_table","create_round_robin","sync_placement_playoffs"):
        assert f"def {name}(" not in APP

def test_unused_imports_removed():
    for symbol in ("OFFICIAL_PUBLIC_BASE_URL","LEGACY_STREAMLIT_BASE_URL","score_model","ortools_available","smtp_configured","is_public_status","is_editable_status","ADMIN_SECTIONS","human_error_id"):
        assert symbol not in APP

def test_bracket_display_uses_aggregate_query():
    block=APP[APP.index("def brackets_for_display"):APP.index("def create_all_group_matches")]
    assert "GROUP BY bracket_id" in block
    assert 'one_row("SELECT COUNT(*) AS n FROM matches WHERE bracket_id=?' not in block

def test_playoff_group_counts_are_batched():
    block=APP[APP.index("def playoff_specs_for_tournament"):APP.index("def ensure_playoffs_for_schedule")]
    assert "GROUP BY group_id" in block
    assert 'one_row("SELECT COUNT(*) AS n FROM teams WHERE group_id=?"' not in block

def test_match_meta_batches_referee_lookup():
    helper=APP[APP.index("def referee_name_map"):APP.index("def match_meta")]
    block=APP[APP.index("def match_meta"):APP.index("def match_result_label")]
    assert "SELECT id,name FROM referees WHERE tournament_id=?" in helper
    assert "referee_name_map(" in block
    assert 'one_row("SELECT name FROM referees WHERE id=?"' not in block
