from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def public_block():
    text = app_text()
    start = text.index("def render_public_view(")
    end = text.index("def render_match_reporter_view(", start)
    return text[start:end]

def test_schema_init_is_process_cached():
    text = app_text()
    assert '@st.cache_resource(show_spinner=False)\ndef init_db():' in text
    assert "_cupnavi_schema_ready" not in text

def test_qr_generation_is_cached():
    text = app_text()
    assert '@st.cache_data(show_spinner=False)\ndef qr_png_bytes(value):' in text

def test_public_view_renders_only_selected_section():
    block = public_block()
    assert "public_section = st.segmented_control(" in block
    assert "schedule, results_tab, tables, statistics" not in block
    assert 'if public_section == tr("Spelschema"):' in block
    assert 'if public_section == tr("Resultat"):' in block
    assert 'if public_section == tr("Partners"):' in block

def test_share_and_qr_are_lazy():
    block = public_block()
    assert "public_share_open_" in block
    share_if = block.index("if share_is_open:")
    qr_render = block.index('render_qr_share_panel(tournament_id, tournament["name"])')
    assert qr_render > share_if

def test_weather_is_opt_in():
    block = public_block()
    assert 'tr("Visa väderprognos")' in block
    assert "if show_weather:" in block
    assert 'fetch_weather_forecast(tournament["location"] or "")' in block

def test_result_events_are_loaded_only_inside_result_section():
    block = public_block()
    result_if = block.index('if public_section == tr("Resultat"):')
    event_query = block.index("SELECT s.match_id, p.name AS player_name")
    assert event_query > result_if

def test_direct_team_sources_use_prefetched_public_data():
    block = public_block()
    assert "def _public_source_team_id(source):" in block
    assert "if team_id in public_team_names:" in block
