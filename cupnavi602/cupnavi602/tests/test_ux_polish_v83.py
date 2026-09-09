from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_public_share_is_compact():
    assert 'with st.popover("Dela"' in APP
    assert "cn-share-metrics-anchor" in APP
