from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v575_release_is_synchronized():
    assert "2026.09.09-575-FORM-UX-PRIORITY-HIERARCHY" in APP
    assert "2026.09.09-575-FORM-UX-PRIORITY-HIERARCHY" in VERSION


def test_cupinfo_explains_now_later_and_advanced():
    assert "Det här behöver du göra nu" in APP
    assert "Kan fyllas i senare" in APP
    assert "Avancerat" in APP
    assert "arrangemangstyp, deltagarklasser samt planer och tider" in APP


def test_team_form_prioritizes_minimum_required_data():
    assert "Måste fyllas i nu:" in APP
    assert "Kan fyllas i senare: tröjor, lagansvarig, kontaktuppgifter och reseönskemål." in APP
    assert "Tröj setup · kan göras senare" in APP
    assert "Kan fyllas i senare · tröjor, kontakt och resor" in APP


def test_rules_progressively_disclose_advanced_settings():
    assert "Måste vara rätt · Match" in APP
    assert "Måste vara rätt · Poäng" in APP
    assert 'with st.expander("Kan finjusteras · tabell, slutspel och schemaprinciper", expanded=False):' in APP
    assert "Standardvärdena fungerar som utgångspunkt." in APP


def test_existing_safety_contract_stays_visible():
    assert "CupNavi flyttar aldrig redan spelade matcher automatiskt" in APP
    assert "schedule_dirty=1" in APP


def test_v574_multi_strategy_kit_search_is_retained():
    kit = (ROOT / "cupnavi_core" / "ai_kit_suggestion.py").read_text(encoding="utf-8")
    assert "MAX_SEARCH_ATTEMPTS = 3" in kit
    assert "Exakt lag + cupkontext" in kit
    assert "Klubbnamn utan ungdomssuffix" in kit
    assert "Lokala och visuella källor" in kit
    assert 'if result.get("found")' in kit
