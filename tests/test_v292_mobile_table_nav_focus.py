from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text(encoding="utf-8")


def test_mobile_standings_use_compact_layout_and_qualifier_labels():
    assert "@media(max-width:600px)" in PRESENTATION
    assert ".texttv-table{{table-layout:fixed;font-size:12px}}" in PRESENTATION
    assert ".texttv-table th:nth-child(7),.texttv-table td:nth-child(7)" in PRESENTATION
    assert ".texttv-table th:nth-child(8),.texttv-table td:nth-child(8)" in PRESENTATION
    assert "content:'Vidare'" in PRESENTATION
    assert "qualifier-mobile" in PRESENTATION
    assert 'mobile_qualifier = f"{rank_value}:a"' in PRESENTATION


def test_public_navigation_has_full_row_brand_background_and_active_contrast():
    assert "background:#1f6f4a !important" in STYLE
    assert "color:#f8fffb !important" in STYLE
    assert ".cn-public-section-nav a.active{background:#ffffff !important;color:#14552f !important" in STYLE


def test_v292_release_is_canonical():
    expected = "2026.08.31-353-GROUP-FLOW-PITCH-TIMING"
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == expected
    assert expected in APP
    assert expected in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
