from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_public_view_tracks_visits_only_in_public_renderer():
    text = app_text()
    start = text.index("def render_public_view(")
    block = text[start:start+500]
    assert "track_public_visit(tournament_id)" in block

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
    assert '("Besöksstatistik", tr("Besök"))' in text
    assert 'if admin_page == "Besöksstatistik":' in text
    assert '"Unika sessioner"' in text
    assert '"Sidvisningar"' in text
    assert '"Aktiva senaste 30 min"' in text
    assert "#### Enheter" in text
    assert "#### Webbläsare" in text
    assert "#### Trafikkälla" in text
    assert "#### Senaste besöken" in text

def test_tracking_has_60_second_view_throttle():
    text = app_text()
    assert "total_seconds() >= 60" in text

def test_schema_migration_v4_exists():
    text = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = 4" in text
    assert '"visitor_analytics"' in text
    assert "idx_visitor_sessions_tournament_first" in text
