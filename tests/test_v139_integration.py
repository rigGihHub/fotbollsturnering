from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

def test_v139_version_sync():
    v=(ROOT/"VERSION.txt").read_text().strip()
    assert v=="2026.08.28-252-CODE-REGEN-CONFIRM"
    assert v in APP
    assert v in (ROOT/"cupnavi_core/version.py").read_text()

def test_admin_uses_task_based_organizer():
    assert 'with st.expander("Förberedelser i detalj", expanded=False)' in APP
    assert "Nästa steg" in APP
    assert "organizer_workflow(" in APP

def test_friendly_error_persists_sanitized_diagnostic():
    assert "safe_error_record(" in APP
    assert "persist_error(con, record)" in APP

def test_ci_quality_gate_exists():
    assert (ROOT/".github/workflows/v139-quality.yml").exists()

def test_architecture_seam_has_no_streamlit():
    text=(ROOT/"cupnavi_core/services.py").read_text()
    assert "import streamlit" not in text
