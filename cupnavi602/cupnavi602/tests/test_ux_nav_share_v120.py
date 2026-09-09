from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_share_expands_in_place_without_navigation():
    assert 'with st.popover("Dela"' in APP
    assert "WhatsApp" in APP and "SMS" in APP and "E-post" in APP
