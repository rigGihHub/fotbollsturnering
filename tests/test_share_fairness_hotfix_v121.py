from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
def test_share_uses_same_page_native_popover():
    start=APP.index("# Kompakt delning direkt kopplad till cupheadern")
    end=APP.index('# v143: mobil först',start)
    block=APP[start:end]
    assert 'with st.popover("Dela"' in block
    assert "share_qr = qr_png_bytes(share_url)" in block
    assert "target='_blank'" not in block
def test_fairness_query_remains_robust():
    assert 'SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL ORDER BY scheduled_start,pitch_number,id' in APP
    assert 'Fairnessanalysen kunde inte beräknas just nu. Övrig cupdata påverkas inte.' in APP
