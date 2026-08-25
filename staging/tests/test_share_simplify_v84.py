from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_share_panel_has_one_primary_share_button():
    text = app_text()
    start = text.index("def share_panel_html(")
    end = text.index("def render_share_panel(", start)
    block = text[start:end]
    assert block.count('id="nativeShare"') == 1
    assert "navigator.share" in block

def test_direct_channel_buttons_are_removed():
    text = app_text()
    start = text.index("def share_panel_html(")
    end = text.index("def render_share_panel(", start)
    block = text[start:end]
    assert "wa.me" not in block
    assert "mailto:" not in block
    assert "sms:?body=" not in block
    assert "fb-messenger://" not in block

def test_share_fallback_copies_current_cup_link():
    text = app_text()
    start = text.index("def share_panel_html(")
    end = text.index("def render_share_panel(", start)
    block = text[start:end]
    assert "navigator.clipboard.writeText(shareData.url)" in block
    assert "share_url = public_cup_url(tournament_id)" in block
