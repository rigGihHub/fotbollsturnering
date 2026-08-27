from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_share_popover_has_light_scoped_surface():
    assert "SHARE POPOVER POLISH v1.195" in APP
    assert '[data-testid="stPopoverBody"]:has(.cn-share-popover-marker)' in APP
    assert "background:#ffffff!important" in APP
    assert "color-scheme:light!important" in APP

def test_share_actions_are_readable_and_active():
    assert '[data-testid="stLinkButton"] a' in APP
    assert 'color:#174d2f!important' in APP
    assert 'opacity:1!important' in APP

def test_share_content_has_qr_guidance_and_public_link_note():
    assert 'st.markdown("#### QR-kod")' in APP
    assert "Skanna koden för att öppna den publika cupsidan." in APP
    assert "kräver ingen inloggning" in APP

def test_visible_version_is_195():
    assert 'Version v.1.232' in APP
