from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_share_is_isolated_in_streamlit_fragment():
    text = app_text()
    start = text.index("# En enda delningsingång bredvid logotypen.")
    end = text.index("with st.container(border=True):", start)
    block = text[start:end]
    assert "@st.fragment" in block
    assert "def render_public_share_fragment" in block
    assert "render_public_share_fragment()" in block
    # Delningsklicket får inte tvinga en full app-rerun.
    assert "st.rerun()" not in block


def test_share_panel_has_light_scoped_styles_and_lazy_qr():
    text = app_text()
    start = text.index("# En enda delningsingång bredvid logotypen.")
    end = text.index("with st.container(border=True):", start)
    block = text[start:end]
    assert "cn-share-url-box" in block
    assert "#f7faf8" in block
    assert "share_qr = qr_png_bytes(share_url)" in block
    assert block.index("share_qr = qr_png_bytes(share_url)") > block.index("if st.session_state[share_visible_key]:")


def test_public_match_metrics_merge_played_and_total():
    text = app_text()
    marker = "if public_page == \"Matcher\":"
    start = text.index(marker)
    end = text.index("public_event_rows = all_rows(", start)
    block = text[start:end]
    assert "{len(played_matches)} {html.escape(tr(\"av\"))} {len(published_matches)}" in block
    assert "<div class='label'>{html.escape(tr(\"Spelade\"))}</div>" not in block
