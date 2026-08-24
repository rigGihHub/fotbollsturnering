from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_share_uses_same_page_light_dismiss_popover():
    text = app_text()
    start = text.index("# En enda delningsingång bredvid logotypen.")
    block = text[start:text.index("with st.container(border=True):", start)]
    assert "popovertarget=" in block
    assert "popover='auto'" in block
    assert "target='_blank'" not in block
    assert "<details class='cn-fixed-share'>" not in block
    assert "share=1#cn-share-section" not in block
    assert "loading='lazy'" in block


def test_fairness_query_uses_robust_full_match_rows_and_cannot_crash_admin():
    text = app_text()
    assert 'SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id' in text
    assert '(int(tid),)' in text
    assert 'Fairnessanalysen kunde inte beräknas just nu. Övrig cupdata påverkas inte.' in text
    assert 'except Exception as exc:' in text
