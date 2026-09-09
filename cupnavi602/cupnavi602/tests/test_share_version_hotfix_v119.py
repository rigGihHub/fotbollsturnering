from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_share_is_same_page_native_control():
    assert 'with st.popover("Dela"' in APP
    assert ".cn-share-metrics-anchor + div" in APP
