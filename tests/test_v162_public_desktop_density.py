from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
UI=APP+"\n"+STYLE
VERSION=(ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
MATCH=(ROOT/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
FEED=(ROOT/"cupnavi_core/public_match_feed_logic.py").read_text(encoding="utf-8")
MATCHES=(ROOT/"cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
RELEASE="2026.08.29-303-PUBLIC-MATCH-EVENT-ROW-NORMALIZATION"

def test_release_version_is_hard_synced():
    assert RELEASE in APP
    assert f'APP_VERSION = "{RELEASE}"' in VERSION
    assert (ROOT/"VERSION.txt").read_text().strip()==RELEASE

def test_desktop_public_view_is_compacted_without_mobile_override():
    assert "@media(min-width:901px)" in UI
    assert ".cup-hero{padding:13px 18px!important" in UI
    assert ".public-match-card{margin:7px 0!important" in UI
    assert "@media(max-width:760px)" in UI

def test_duplicate_next_match_hero_is_removed():
    assert 'class="cn-next-match"' not in MATCHES
    assert "Cupen just nu" in FEED

def test_information_screen_is_demoted_to_info_page():
    start=WORKSPACE.index("public_page = resolve_public_page(")
    end=WORKSPACE.index("def _filter_public_matches",start)
    block=WORKSPACE[start:end]
    assert "screen_url = public_cup_url" in block
    assert 'if public_page == "Info":' in block

def test_follow_team_does_not_require_keyed_container_support():
    assert 'st.container(key=f"public_follow_{tournament_id}")' not in APP
    assert "cn-public-follow-anchor" in UI

def test_match_secondary_information_is_visually_secondary():
    assert "public-match-secondary" in APP
    assert "<small class=\"kit-label\">Hemmalag</small>" in MATCH
