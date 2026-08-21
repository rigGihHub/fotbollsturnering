from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_public_share_contains_qr_share_panel():
    text = app_text()
    start = text.index("def render_public_view(")
    block = text[start:start+8000]
    assert 'render_qr_share_panel(tournament_id, tournament["name"])' in block
    assert 'tr("Dela länken eller QR-koden till den här cupen.")' in block

def test_qr_can_share_png_file():
    text = app_text()
    start = text.index("def qr_share_panel_html(")
    end = text.index("def render_qr_share_panel(", start)
    block = text[start:end]
    assert "navigator.canShare" in block
    assert "files:[file]" in block
    assert "new File([blob]" in block
    assert "image/png" in block

def test_qr_has_download_fallback():
    text = app_text()
    start = text.index("def qr_share_panel_html(")
    end = text.index("def render_qr_share_panel(", start)
    block = text[start:end]
    assert 'download="' in block
    assert 'link.download = filename' in block

def test_old_ux_history_files_removed_from_release_tree():
    ux_files = list(Path(".").glob("UX_V*.md"))
    assert ux_files == []
