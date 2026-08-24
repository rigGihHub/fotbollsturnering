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
    assert "@st.cache_resource(show_spinner=False)" in text
    assert "def init_db():" in text

def test_qr_generation_is_cached():
    text = app_text()
    assert "@st.cache_data(show_spinner=False)" in text
    assert "def qr_png_bytes(value):" in text

def test_public_view_renders_only_selected_main_page():
    block = public_block()
    assert 'if public_page == "Matcher":' in block
    assert 'if public_page == "Statistik":' in block
    assert 'if public_page == "Info":' in block
    assert "schedule, results_tab, tables, statistics" not in block

def test_share_and_qr_are_lazy():
    block = public_block()
    assert "if share_is_open:" in block
    assert "share_qr = qr_png_bytes(share_url)" in block
    assert block.index("share_qr = qr_png_bytes(share_url)") > block.index("if share_is_open:")

def test_weather_is_opt_in():
    block = public_block()
    assert 'tr("Visa väderprognos")' in block
    assert "show_weather" in block

def test_result_events_are_loaded_only_inside_matches_page():
    block = public_block()
    matcher_if = block.index('if public_page == "Matcher":')
    event_query = block.index("SELECT s.match_id, p.name AS player_name")
    assert event_query > matcher_if
