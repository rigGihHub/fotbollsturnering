from pathlib import Path
APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_team_page_cleanup_contract():
    start = APP.index('if admin_page == "Lag":')
    end = APP.index('if admin_page == "Grupper":', start)
    block = APP[start:end]
    assert 'st.markdown("#### Tävlingsklasser")' in block
    assert "Hantera tävlingsklasser i Adminöversikt" in block
    assert "Digital lagincheckning" in block
