from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
RELEASE="2026.08.26-193-FULL-UI-UX-REDESIGN"

def test_release_version_is_hard_synced():
    assert RELEASE in APP
    assert f'APP_VERSION = "{RELEASE}"' in VERSION
    assert (ROOT/"VERSION.txt").read_text().strip()==RELEASE

def test_desktop_public_view_is_compacted_without_mobile_override():
    assert "@media(min-width:901px)" in APP
    assert ".cup-hero{padding:13px 18px!important" in APP
    assert ".public-match-card{margin:7px 0!important" in APP
    assert "@media(max-width:760px)" in APP

def test_duplicate_next_match_hero_is_removed():
    public=APP[APP.index('if public_page == "Matcher":'):APP.index('if public_page == "Statistik":')]
    assert 'class="cn-next-match"' not in public
    assert "Cupen just nu" in public

def test_information_screen_is_demoted_to_info_page():
    start=APP.index("public_page = st.session_state[public_page_key]")
    end=APP.index("cup_key = quote(",start)
    block=APP[start:end]
    assert "screen_url = public_cup_url" in block
    assert 'if public_page == "Info":' in block

def test_follow_team_does_not_require_keyed_container_support():
    assert 'st.container(key=f"public_follow_{tournament_id}")' not in APP
    assert "cn-public-follow-anchor" in APP

def test_match_secondary_information_is_visually_secondary():
    assert "public-match-secondary" in APP
    assert "<small class=\"kit-label\">Hemmalag</small>" in APP
