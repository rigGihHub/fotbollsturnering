from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
def test_schema_init_is_process_cached():
    assert "@st.cache_resource(show_spinner=False)" in APP
    assert "def init_db():" in APP
def test_qr_generation_is_cached():
    assert "@st.cache_data(show_spinner=False)" in APP
    assert "def qr_png_bytes(value):" in APP
def test_public_view_renders_only_selected_main_page():
    assert 'if public_page == "Matcher":' in APP
    assert 'if public_page == "Statistik":' in APP
    assert 'if public_page == "Info":' in APP
def test_share_qr_uses_cached_generator_inside_popover():
    start=APP.index("# Kompakt delning direkt kopplad till cupheadern")
    end=APP.index('# v143: mobil först',start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "share_qr = qr_png_bytes(share_url)" in block
def test_weather_is_opt_in():
    assert 'tr("Visa väderprognos")' in APP
