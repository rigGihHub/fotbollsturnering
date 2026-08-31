from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

def _block(start_marker,end_marker):
    start=APP.index(start_marker); end=APP.index(end_marker,start); return APP[start:end]

def test_admin_overview_hides_secondary_dashboard_detail():
    block=_block('elif admin_page == "Adminöversikt":','if admin_page == "Cupinställningar":')
    for removed in ("#### 📱 Snabbadmin", "Förberedelser i detalj", "Driftstatus", "Genvägar & publik vy", "Checklista inför cupstart"):
        assert removed not in block
    assert 'next_step = recommend_next_step(' in block
    assert 'key=f"dashboard_next_step_{tid}"' in block
    assert '"Visa fler verktyg på översikten"' in block

def test_admin_overview_advanced_tools_are_explicit_opt_in():
    block=_block('elif admin_page == "Adminöversikt":','if admin_page == "Cupinställningar":')
    assert 'if show_overview_advanced:' in block
    assert 'with st.expander("⚖️ Fairnessanalys", expanded=False):' in block
    assert 'show_direct_edit = st.toggle(' in block

def test_controls_put_domain_checks_before_technical_tools():
    block=_block('if admin_page == "Kontroller":','if admin_page == "Lag":')
    core=block.index('control_rules = one_row('); technical=block.index('st.toggle("Visa teknisk hälsa och backup"')
    assert core < technical
    assert 'st.toggle("Fördjupad kontroll"' in block

def test_controls_keep_blockers_visible():
    block=_block('if admin_page == "Kontroller":','if admin_page == "Lag":')
    assert 'cc1.metric("Blockerande fel", len(control_errors))' in block
    assert 'st.error("Publicering är blockerad tills följande fel är åtgärdade:")' in block
    assert 'st.warning("Följande varningar behöver granskas före publicering:")' in block
