from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_render_local_derived_cache_exists_and_is_invalidated_with_query_cache():
    assert "_DERIVED_RENDER_CACHE = {}" in APP
    block=APP[APP.index("def _clear_render_query_cache"):APP.index("def all_rows")]
    assert "_DERIVED_RENDER_CACHE.clear()" in block

def test_match_meta_uses_o1_number_map_not_linear_scan_each_call():
    block=APP[APP.index("def match_number_map"):APP.index("def match_meta")]
    assert 'return {int(row["id"]): index' in block
    match_meta=APP[APP.index("def match_meta"):APP.index("def match_result_label")]
    assert "next((index for index" not in match_meta
    assert "match_number_map(" in match_meta

def test_group_tables_are_cached_per_render():
    block=APP[APP.index("def calculate_table"):APP.index("def final_ranking_rows")]
    assert 'table_key = (' in block
    assert '_DERIVED_RENDER_CACHE[table_key] = result' in block

def test_pitch_creation_and_travel_writes_are_batched():
    ensure=APP[APP.index("def ensure_pitch_definitions"):APP.index("def save_pitch_name")]
    travel=APP[APP.index("def save_pitch_travel_time"):APP.index("def pitch_name_map")]
    assert "run_many(" in ensure
    assert "run_many(" in travel

def test_public_groups_are_loaded_only_inside_statistics_fragment():
    stats=APP[APP.index("def render_public_statistics_section"):APP.index("def render_public_info_section")]
    assert 'groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name"' in stats
    assert 'forecast_groups = all_rows("SELECT * FROM groups WHERE tournament_id=? ORDER BY name"' in stats

def test_source_resolution_and_labels_have_render_local_cache():
    resolve=APP[APP.index("def resolve_source"):APP.index("def match_meta")]
    assert '("resolved-source"' in resolve
    assert '("source-label"' in resolve
