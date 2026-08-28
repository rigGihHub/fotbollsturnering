from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_share_uses_supported_native_popover_structure():
    assert 'with st.popover("Dela"' in APP
    assert "st.container(border=True)" not in APP[APP.index("def render_public_share_control("):APP.index('# v143: mobil först')]
