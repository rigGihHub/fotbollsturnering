from pathlib import Path

def test_feedback_email_persisted():
    text=Path("app.py").read_text(encoding="utf-8")
    assert "feedback_email TEXT" in text
    assert "ALTER TABLE tournaments ADD COLUMN feedback_email TEXT" in text
    assert "feedback_email=?" in text

def test_feedback_email_admin_input():
    text=Path("app.py").read_text(encoding="utf-8")
    assert '"E-post för feedback"' in text
    assert "edited_feedback_email.strip()" in text

def test_public_mailto_button():
    text=Path("app.py").read_text(encoding="utf-8")
    assert "Frågor eller feedback" in text
    assert "href='mailto:" in text
    assert "cn-email-button" in text
