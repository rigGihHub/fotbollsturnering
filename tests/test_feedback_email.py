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
    app=Path("app.py").read_text(encoding="utf-8")
    info=Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
    combined=app+info
    assert "Frågor eller feedback" in combined
    assert "href='mailto:" in info
    assert "cn-email-button" in combined
