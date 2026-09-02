from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")


def test_v284_release_and_extracted_setup_module_exist():
    assert "2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP" in APP
    assert "class InitialSetupDependencies" in VIEW
    assert "def render_initial_tournament_setup" in VIEW


def test_app_keeps_thin_setup_wrapper_and_injects_existing_services():
    start = APP.index("def render_initial_tournament_setup")
    end = APP.index("def _render_with_friendly_error", start)
    block = APP[start:end]
    assert "render_initial_tournament_setup_module(" in block
    assert "autosave_rule_field=_autosave_rule_field" in block
    assert "autosave_tournament_field=_autosave_tournament_field" in block
    assert "db=db" in block
    assert "st.markdown(\"### 2. Kapacitet & speltider\")" not in block


def test_extracted_view_owns_complete_guided_setup_flow():
    for marker in (
        "cn-setup-hero",
        "### 1. Vilka ska spela?",
        "### 2. Vad har ni tillgång till?",
        'with st.expander("Sportprofil", expanded=False):',
        "### 3. Rekommenderat tävlingsformat",
        "### 4. Matchregler och hårda begränsningar",
        "### 5. Vad är viktigast i schemat?",
        "### 6. Arrangemang & deltagarservice",
        "### 7. Redo att fortsätta",
        "Fortsätt → Lägg till lag",
    ):
        assert marker in VIEW


def test_setup_view_does_not_import_app_or_own_schedule_engine():
    assert "import app" not in VIEW
    assert "from app import" not in VIEW
    assert "def generate_schedule" not in VIEW
    assert "def _set_publication_if_current" not in VIEW
