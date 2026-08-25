from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_share_uses_native_streamlit_components_not_raw_button_html():
    text = app_text()
    start = text.index("# En enda delningsingång bredvid logotypen.")
    end = text.index("\n    render_public_share_fragment()", start)
    block = text[start:end]
    assert "st.button(" in block
    assert "with st.container(border=True):" in block
    assert "cn-share-panel-anchor" in block
    assert "<button type=" not in block
    assert "popovertarget=" not in block
    assert "popover='auto'" not in block


def test_share_qr_is_generated_only_when_panel_is_open():
    text = app_text()
    start = text.index("# En enda delningsingång bredvid logotypen.")
    end = text.index("\n    render_public_share_fragment()", start)
    block = text[start:end]
    open_pos = block.index("if st.session_state[share_visible_key]:")
    qr_pos = block.index("share_qr = qr_png_bytes(share_url)")
    assert qr_pos > open_pos
