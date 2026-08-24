from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_integrated_share_contract_replaces_legacy_share_panel():
    text = app_text()
    start = text.index("def render_public_view(")
    block = text[start:text.index("def render_match_reporter_view(", start)]
    assert "popovertarget=" in block
    assert "popover='auto'" in block
    assert "share_qr = qr_png_bytes(share_url)" in block
    assert "share=1#cn-share-section" not in block
    assert "render_qr_share_panel(tournament_id" not in block


def test_schema_regressions_must_follow_current_schema_constant():
    migrations = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = 12" in migrations


def test_privacy_contract_is_player_name_only():
    text = app_text()
    assert "Skyddad spelare" in text
    assert "Skyddade kontaktuppgifter – får inte visas publikt" not in text
