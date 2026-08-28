
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def _block(start_marker,end_marker):
    start=APP.index(start_marker)
    end=APP.index(end_marker,start)
    return APP[start:end]


def test_admin_overview_hides_secondary_dashboard_detail():
    block=_block('if admin_page == "Adminöversikt":','if admin_page == "Cupinställningar":')
    for label in [
        'with st.expander("Förberedelser i detalj", expanded=False)',
        'with st.expander("Genvägar & publik vy", expanded=False)',
        'with st.expander("Direktredigera cupinställningar", expanded=False)',
        'with st.expander("Publicering & startkontroll", expanded=False)',
        'with st.expander("⚠️ Riskzon – Cup och papperskorg", expanded=False)',
        'with st.expander("Testverktyg", expanded=False)',
    ]:
        assert label in block
    assert "next_step_title" in block
    assert 'key=f"dashboard_next_step_{tid}"' in block


def test_admin_overview_live_drift_status_can_expand_automatically():
    block=_block('if admin_page == "Adminöversikt":','if admin_page == "Cupinställningar":')
    assert 'with st.expander("Driftstatus", expanded=current_admin_mode == "live")' in block
    assert 'metric("Kommande matcher"' in block
    assert 'metric("Problem"' in block


def test_controls_put_domain_checks_before_technical_tools():
    block=_block('if admin_page == "Kontroller":','if admin_page == "Lag":')
    core=block.index('control_rules = one_row(')
    technical=block.index('with st.expander("Teknisk hälsa och backup", expanded=False)')
    assert core < technical
    assert 'with st.expander("Fördjupad kontroll", expanded=False)' in block


def test_controls_keep_blockers_visible():
    block=_block('if admin_page == "Kontroller":','if admin_page == "Lag":')
    assert 'cc1.metric("Blockerande fel", len(control_errors))' in block
    assert 'st.error("Publicering är blockerad tills följande fel är åtgärdade:")' in block
    assert 'st.warning("Följande varningar behöver granskas före publicering:")' in block
