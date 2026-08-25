from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
RELEASE="2026.08.25-163-PUBLIC-RUNTIME-FIX"

def test_release_version_is_hard_synced():
    assert RELEASE in APP
    assert f'APP_VERSION = "{RELEASE}"' in VERSION
    assert (ROOT/"VERSION.txt").read_text().strip()==RELEASE

def test_desktop_public_view_is_compacted_without_mobile_override():
    assert "@media(min-width:901px)" in APP
    assert ".cup-hero{padding:16px 20px!important" in APP
    assert ".public-match-card{margin:7px 0!important" in APP
    assert "@media(max-width:760px)" in APP

def test_duplicate_next_match_hero_is_removed():
    public=APP[APP.index('if public_page == "Matcher":'):APP.index('if public_page == "Statistik":')]
    assert 'class="cn-next-match"' not in public
    assert "Cupen just nu" in public

def test_information_screen_is_demoted_to_info_page():
    block=APP[APP.index("screen_url = public_cup_url"):APP.index("# En enda delningsingång",APP.index("screen_url = public_cup_url"))]
    assert 'if public_page == "Info":' in block

def test_follow_team_does_not_require_keyed_container_support():
    assert 'st.container(key=f"public_follow_{tournament_id}")' not in APP
    assert "cn-public-follow-anchor" in APP

def test_match_secondary_information_is_visually_secondary():
    assert "public-match-secondary" in APP
    assert "<small class=\"kit-label\">Hemmalag</small>" in APP
