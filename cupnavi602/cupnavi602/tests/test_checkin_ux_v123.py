from pathlib import Path
APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_team_page_cleanup_contract():
    start = APP.index('if admin_page == "Lag":')
    end = APP.index('if admin_page == "Grupper":', start)
    block = APP[start:end]
    assert '"Hantera tävlingsklasser"' in block
    assert '"Hantera tävlingsklasser"' in block
    assert 'if st.toggle("Digital lagincheckning", value=False, key=f"lazy_team_checkin_{tid}"' in block
