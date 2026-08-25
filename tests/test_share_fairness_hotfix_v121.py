from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_share_uses_same_page_native_toggle_panel():
    text = app_text()
    start = text.index("# En enda delningsingång bredvid logotypen.")
    block = text[start:text.index("\n    render_public_share_fragment()", start)]
    assert "cn_share_visible_" in block
    assert "cn_share_button_" in block
    assert "cn-share-panel-anchor" in block
    assert "if st.session_state[share_visible_key]:" in block
    assert "target='_blank'" not in block
    assert "popovertarget=" not in block
    assert "popover='auto'" not in block
    assert "share_qr = qr_png_bytes(share_url)" in block


def test_fairness_query_uses_robust_full_match_rows_and_cannot_crash_admin():
    text = app_text()
    assert 'SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id' in text
    assert '(int(tid),)' in text
    assert 'Fairnessanalysen kunde inte beräknas just nu. Övrig cupdata påverkas inte.' in text
    assert 'except Exception as exc:' in text
