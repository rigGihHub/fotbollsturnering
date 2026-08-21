from pathlib import Path

def test_instagram_is_persisted():
    text=Path("app.py").read_text(encoding="utf-8")
    assert "instagram_url TEXT" in text
    assert "ALTER TABLE tournaments ADD COLUMN instagram_url TEXT" in text
    assert "instagram_url=?" in text

def test_admin_accepts_instagram():
    text=Path("app.py").read_text(encoding="utf-8")
    assert '"Instagram för cupen"' in text
    assert "edited_instagram.strip()" in text

def test_public_instagram_follow_button():
    text=Path("app.py").read_text(encoding="utf-8")
    assert "📷 Följ cupen" in text
    assert "https://www.instagram.com/" in text
    assert "cn-instagram-button" in text
