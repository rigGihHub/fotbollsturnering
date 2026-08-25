from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.25-182-SIDEBAR-VERSION"

def test_final_ranking_has_schema_fallback():
    assert "Fall back to the pre-v176 columns" in APP
    assert 'item["planned_team_count"] = 0' in APP

def test_group_qualifiers_derive_from_real_brackets():
    assert "def group_playoff_qualifiers" in APP
    assert 'lower_name.startswith("a-")' in APP
    assert ".texttv-table tr.qual-a td" in APP
    assert ".texttv-table tr.qual-b td" in APP

def test_cupinfo_matches_main_navigation():
    assert "nav1, nav2, nav3, nav4, nav5 = st.columns(5)" in APP
    assert '(nav5, "Info", "ℹ️", "Cupinfo")' in APP
    assert "public_info_secondary_" not in APP

def test_database_is_hidden_in_tournament_view():
    assert 'if st.session_state.get("view_mode") != "Turneringsvy":' in APP

def test_logo_and_nav_have_more_clear_space():
    assert ".cn-mode-nav-safezone{height:72px!important;display:block!important}" in APP
    assert "width:min(100%, 190px);" in APP

def test_share_button_is_integrated_in_hero_area():
    assert "margin:-58px 16px 20px auto!important" in APP
    assert "position:fixed;top:14px;left:calc(50% + 184px)" not in APP
    assert "background:rgba(255,255,255,.12)!important;color:#fff!important" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
