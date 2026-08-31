from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_public_view_tracks_visits_only_in_public_renderer():
    block = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
    assert "track_public_visit(tournament_id)" in block
    # Analytics ska ligga efter publiksektionerna så den inte blockerar primärt innehåll.
    assert block.rfind("track_public_visit(tournament_id)") > block.rfind("render_public_info_section")

def test_visitor_analytics_does_not_store_ip_address():
    text = app_text()
    assert "CREATE TABLE IF NOT EXISTS visitor_sessions" in text
    schema = text[
        text.index("CREATE TABLE IF NOT EXISTS visitor_sessions"):
        text.index("CREATE TABLE IF NOT EXISTS groups")
    ]
    assert "ip_address" not in schema.lower()
    assert "remote_addr" not in text.lower()

def test_admin_has_detailed_visitor_statistics_page():
    text = app_text()
    assert 'args=("Besöksstatistik",)' in text
    assert 'if admin_page == "Besöksstatistik":' in text
    assert '"Unika sessioner"' in text
    assert '"Sidvisningar"' in text
    assert '"Aktiva senaste 30 min"' in text
    assert "#### Enheter" in text
    assert "#### Webbläsare" in text
    assert "#### Trafikkälla" in text
    assert 'with st.expander("Senaste besök & integritet", expanded=False)' in text

def test_tracking_throttles_repeat_writes_for_at_least_five_minutes():
    text = app_text()
    assert "total_seconds() >= 300" in text

def test_schema_migration_v4_exists():
    text = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION =" in text
    assert "Migration(\n        7," in text
    assert '"visitor_analytics"' in text
    assert "idx_visitor_sessions_tournament_first" in text
