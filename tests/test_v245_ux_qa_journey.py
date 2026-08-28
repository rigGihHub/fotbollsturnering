
from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_overview_reuses_existing_schedule_validation():
    block=APP[APP.index('with st.expander("Publicering & startkontroll", expanded=False):'):
              APP.index('with st.expander("⚠️ Riskzon – Cup och papperskorg", expanded=False):')]
    assert "overview_schedule_errors = sidebar_errors" in block
    assert "overview_schedule_warnings = sidebar_warnings" in block
    assert "validate_schedule(tid, tournament, overview_rules)" not in block

def test_overview_does_not_duplicate_publication_dashboard():
    block=APP[APP.index('with st.expander("Publicering & startkontroll", expanded=False):'):
              APP.index('with st.expander("⚠️ Riskzon – Cup och papperskorg", expanded=False):')]
    assert 'st.subheader("Publicering")' not in block
    assert 'metric("Publicerade"' not in block
    assert "Publiceringsstatus och publiceringsknapp finns i vänsterspalten." in block

def test_results_page_uses_navigation_terminology():
    block=APP[APP.index('if admin_page == "Matcher och resultat":'):
              APP.index('if admin_page == "Matchhändelser":')]
    assert 'st.header("Resultat")' in block
    assert 'st.header("Matcher & resultat")' not in block

def test_secondary_guidance_is_visually_quieter():
    assert 'st.caption("Lag kan bara placeras i grupper inom samma tävlingsklass.")' in APP
    assert 'st.caption("Knappen ovan skapar gruppspel, slutspel och spelschema i ett steg.")' in APP
    assert 'st.caption("PDF-export blir tillgänglig när ett schema finns.")' in APP
