from pathlib import Path
APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_team_page_cleanup_contract():
    start = APP.index('if admin_page == "Lag":')
    end = APP.index('if admin_page == "Grupper":', start)
    block = APP[start:end]
    assert 'with st.expander("Tävlingsklasser", expanded=False)' in block
    assert '"Hantera tävlingsklasser"' in block
    assert 'with st.expander("Digital lagincheckning", expanded=False)' in block
