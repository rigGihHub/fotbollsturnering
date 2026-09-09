from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text(encoding="utf-8")
VERSION = "2026.09.09-597-RELEASE-GATE-CLEANUP-FULL-REGRESSION"


def test_release_identity_is_synchronized():
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    core = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert f'APP_VERSION = "{VERSION}"' in core


def test_startup_version_contract_is_importable():
    version_file = ROOT / "cupnavi_core" / "version.py"
    spec = importlib.util.spec_from_file_location("cupnavi_version_v597", version_file)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    assert module.release_ui_label(module.APP_VERSION) == f"CupNavi {VERSION}"


def test_current_plan_flow_replaces_superseded_v566_copy_without_losing_requirements():
    block = APP.split('elif admin_page == "Planer & tider":', 1)[1].split('elif admin_page == "Adminöversikt":', 1)[0]
    assert "### 1. Hur många planer har ni?" in block
    assert "### 2. När kan planerna användas?" in block
    assert "✓ Obligatoriska planuppgifter är klara." in block
    assert "Valfritt: adresser och restid mellan planer" in block
    assert "Fortsätt till Domare →" in block
    assert "Rätta plantiderna ovan innan du går vidare." in block


def test_referees_remain_explicitly_optional_and_have_one_forward_handoff():
    block = APP.split('if admin_page == "Domare":', 1)[1].split('def _undo_schedule_change', 1)[0]
    assert "Steg 6 av 9 · Domare · valfritt" in block
    assert "🕒 Senare · fortsätt utan domare just nu" in block
    assert "Cupen kan schemaläggas och publiceras utan domare" in block
    assert block.count("Fortsätt till Schema →") == 1


def test_schedule_navigation_matches_current_nine_step_flow_and_protects_existing_work():
    assert "← Till Domare" in SCHEDULE
    assert "CupNavi skriver aldrig över ett befintligt schema automatiskt" in SCHEDULE
    assert "Spelade matcher och resultat är alltid skyddade." in SCHEDULE
    for label in (
        "### 1. Vad vill du göra med schemat?",
        "### 2. Kontrollera att allt är redo",
        "### 3. Skapa, granska eller justera schemat",
        "### 4. Gå vidare till kontroll",
    ):
        assert label in SCHEDULE


def test_rules_current_copy_preserves_progressive_disclosure_and_played_match_safety():
    block = APP.split('if admin_page == "Regler":', 1)[1].split('if admin_page == "Cupinställningar":', 1)[0]
    assert "### 1. Bestäm det viktigaste" in block
    assert "#### Matchtid" in block
    assert "#### Poäng" in block
    assert "⚙️ Fler regler · tabell, slutspel och schemaprinciper" in block
    assert "Redan spelade matcher flyttas aldrig automatiskt." in block
    assert "schedule_dirty=1" in APP


def test_texttv_table_contract_is_current_and_accessible():
    assert "background:#050705" in PRESENTATION
    assert '<th>Pl</th><th>Lag</th><th>S</th><th>V</th><th>O</th><th>F</th>' in PRESENTATION
    assert "font-variant-numeric:tabular-nums" in PRESENTATION
    assert "Qualification is communicated with accent + label, never colour alone." in PRESENTATION


def test_team_flow_semantics_survive_without_historical_version_pin():
    start = APP.index('if admin_page == "Lag":')
    end = APP.index('if admin_page == "Tröj setup":', start)
    block = APP[start:end]
    assert "När laglistan är klar går du vidare till Grupper. Allt annat på sidan är valfritt." in block
    assert "Fortsätt till Grupper →" in block
    assert 'with st.expander("Valfritt · komplettera laget senare", expanded=False):' in block
