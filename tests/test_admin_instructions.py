from pathlib import Path

def test_instructions_are_admin_navigation_page():
    text=Path("app.py").read_text(encoding="utf-8")
    assert '"Instruktioner", "Adminöversikt"' in text
    assert '("Instruktioner", tr("Instruktioner"))' in text
    assert 'if admin_page == "Instruktioner":' in text

def test_guide_is_dynamic():
    text=Path("app.py").read_text(encoding="utf-8")
    section=text[text.index('if admin_page == "Instruktioner":'):text.index('elif admin_page == "Adminöversikt":')]
    assert "_admin_workflow_counts(tid)" in section
    assert "guide_scheduled" in section
    assert "tournament[\"schedule_dirty\"]" in section
    assert "tournament[\"is_published\"]" in section
    assert "st.progress(" in section
    assert "Rekommenderat nästa steg" in section

def test_guide_links_to_actual_admin_pages():
    text=Path("app.py").read_text(encoding="utf-8")
    section=text[text.index('if admin_page == "Instruktioner":'):text.index('elif admin_page == "Adminöversikt":')]
    for page in ["Adminöversikt","Lag","Grupper","Trupper","Domare","Skapa och publicera schema","Kontroller","Matcher och resultat","Matchhändelser","Tabeller"]:
        assert f'"page": "{page}"' in section

def test_guide_mentions_current_automatic_behaviors():
    text=Path("app.py").read_text(encoding="utf-8")
    section=text[text.index('if admin_page == "Instruktioner":'):text.index('elif admin_page == "Adminöversikt":')]
    assert "sparas automatiskt" in section
    assert "PDF-paket" in section
    assert "Matcher är samlade på en publik sida" in section
