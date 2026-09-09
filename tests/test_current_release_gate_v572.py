from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
KIT = (ROOT / "cupnavi_core" / "ai_kit_suggestion.py").read_text(encoding="utf-8")
VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v572_release_and_named_kit_setup_page():
    assert "2026.09.09-572-KIT-SETUP-WEB-SCAN" in VERSION
    assert '"Tröj setup"' in APP
    assert 'st.header("👕 Tröj setup")' in APP
    assert '("Tröj setup", "Tröj setup")' in APP


def test_kit_setup_web_scans_all_teams_but_never_auto_saves():
    assert '"tools": [{"type": "web_search"}]' in KIT
    assert '"sources"' in KIT
    assert '🌐 Scanna nätet för alla lag' in APP
    scan = APP.index('🌐 Scanna nätet för alla lag')
    approve = APP.index('✓ Godkänn och spara', scan)
    update = APP.index('UPDATE teams SET primary_color=', approve)
    assert scan < approve < update


def test_each_proposal_is_editable_before_approval_and_sources_visible():
    for label in ["Hemma – mönster", "Hemma – färg 1", "Borta – mönster", "Borta – färg 1"]:
        assert label in APP
    assert "Källor som CupNavi använde" in APP
    assert "CupNavi ger ett förslag – inte ett facit" in APP


def test_kit_setup_remains_editable_later_from_team_page():
    assert 'Redigera under Lag' in APP
    assert 'st.session_state["edit_team"] = team["id"]' in APP
    assert 'if st.toggle("Redigera eller ta bort lag"' in APP
