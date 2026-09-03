from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INFO=(ROOT/"cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_release_version():
    assert VERSION=="2026.09.03-423-PUBLIC-INFO-COLD-START"

def test_info_has_guide_intro_and_scannable_sections():
    assert 'class="cn-info-guide-head"' in INFO
    assert "Allt praktiskt på ett ställe" in INFO
    assert "cn-info-section-title" in INFO

def test_venue_points_are_cards_with_kind_context():
    assert "cn-venue-card" in INFO
    assert "cn-venue-icon" in INFO
    assert "cn-venue-copy" in INFO
    assert "point_kind =" in INFO

def test_practical_info_is_semantic_card_grid():
    assert "cn-practical-item" in INFO
    for token in ("Arena","Kiosk","Omklädningsrum","Priser/avgifter","E-post"):
        assert token in INFO

def test_duplicate_cupkarta_list_is_removed_but_venue_snapshot_remains():
    assert "venue_points_public = all_rows(" in INFO
    assert "Hitta på cupområdet" in INFO
    assert 'st.markdown("### 🗺️ Cupkarta")' not in INFO
    assert "Do not repeat the same places" in INFO

def test_mobile_guide_styles_are_compact():
    for marker in (
        ".cn-info-guide-head{",
        ".cn-info-section-title{",
        ".cn-venue-card{",
        ".cn-practical-info-card{",
        ".cn-practical-item{",
    ):
        assert marker in STYLE
    assert "@media(max-width:680px)" in STYLE
    assert ".cn-practical-info-card{grid-template-columns:1fr!important}" in STYLE
