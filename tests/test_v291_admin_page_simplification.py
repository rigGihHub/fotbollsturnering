from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.08.29-302-PUBLIC-MATCH-EVENT-ROBUSTNESS"
    assert VERSION in APP


def test_instruction_page_is_user_facing_not_meta_documentation():
    assert "Följ cupen steg för steg. Guiden anpassas automatiskt" in APP
    assert "När CupNavi får nya arbetssteg eller funktioner" not in APP


def test_cup_settings_secondary_profile_is_progressively_disclosed():
    assert 'with st.expander("Tävlingsprofil och rekommendation", expanded=False):' in APP
    assert 'Rekommendationen är beslutsstöd och ändrar inte cupen automatiskt.' in APP
    assert 'st.caption("Sportprofil:' not in APP


def test_admin_copy_is_shorter_and_more_task_focused():
    assert "Se vad som blockerar schemat och få förslag på minsta möjliga åtgärd." in APP
    assert "Välj lag och hantera spelare manuellt eller via AI-import." in APP
    assert "Importera lag eller spelare från CSV/Excel med automatisk kolumnmatchning." in APP
    assert "Verktyg för cupdagen, schemajusteringar och felsituationer." in APP


def test_technical_tools_duplicate_label_removed_but_control_remains():
    assert 'st.caption("Tekniska verktyg")' not in APP
    assert 'st.toggle("Visa teknisk hälsa och backup"' in APP
