from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.25-170-FORMAT-RECOMMENDER"

def test_public_has_four_clear_competition_buttons():
    for label in ("Spelschema & resultat","Tabeller gruppspel","Slutspel","Statistik"):
        assert label in APP
    assert "nav1, nav2, nav3, nav4 = st.columns(4)" in APP

def test_sections_have_distinct_urls():
    assert '"tables": "Tabeller"' in APP
    assert '"playoffs": "Slutspel"' in APP
    assert '"stats": "Statistik"' in APP

def test_public_sections_render_directly_without_second_level_segmented_control():
    assert 'forced_section=tr("Tabeller")' in APP
    assert 'forced_section=tr("Slutspel")' in APP
    assert 'forced_section=tr("Topplistor")' in APP

def test_mobile_bottom_nav_matches_competition_flow():
    assert "section=tables" in APP
    assert "section=playoffs" in APP
    assert "<span>Schema</span>" in APP
    assert "<span>Statistik</span>" in APP

def test_info_is_secondary_not_main_competition_button():
    assert "ℹ️ Information om cupen" in APP
    main=APP[APP.index("main_nav = ["):APP.index("_public_section_by_page",APP.index("main_nav = ["))]
    assert '"Info"' not in main

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
