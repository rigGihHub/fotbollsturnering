from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
def test_integrated_share_contract_uses_native_popover():
    start=APP.index("# Kompakt delning direkt kopplad till cupheadern")
    end=APP.index('# v143: mobil först',start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "share_qr = qr_png_bytes(share_url)" in block
    assert "render_qr_share_panel(tournament_id" not in block
def test_schema_regressions_follow_current_schema_constant():
    migrations=Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = " in migrations
def test_privacy_contract_is_player_name_only():
    assert "Skyddad spelare" in APP
