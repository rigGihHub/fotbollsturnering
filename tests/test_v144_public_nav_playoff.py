from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STATS=(ROOT/"cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
PUBLIC_NAV=(ROOT/"cupnavi_core/public_navigation_view.py").read_text(encoding="utf-8")
MATCHES=(ROOT/"cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
FEED=(ROOT/"cupnavi_core/public_match_feed_logic.py").read_text(encoding="utf-8")
SCHEDULE=(ROOT/"cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")

def test_public_navigation_updates_url_section_and_legacy_stats_survives():
    from cupnavi_core.public_view_logic import public_section_for_page, resolve_public_page
    assert public_section_for_page("Mitt lag") == "team"
    assert resolve_public_page("stats") == "Tabeller"
    assert 'href = f"?cup={cup_key}&section={quote(str(section))}{team_query}"' in PUBLIC_NAV
    assert 'st.segmented_control(' in WORKSPACE

def test_played_match_switch_is_url_backed_and_mobile_safe():
    assert 'st.query_params["matches"] = selected_match_view' in MATCHES
    assert 'selected_match_view == "played"' in MATCHES
    assert 'base_match_list = list(played_matches)' in MATCHES

def test_upcoming_match_parsing_is_defensive():
    assert "def _parse_start" in FEED
    assert "except (TypeError, ValueError)" in FEED
    # v162 intentionally removed the duplicate large Next Match hero.
    assert 'class="cn-next-match"' not in MATCHES

def test_public_playoff_distinguishes_configuration_errors():
    assert "Slutspelet kan inte skapas med nuvarande upplägg" in STATS
    assert "Slutspel är valt men slutspelsträdet har ännu inte skapats" in STATS

def test_admin_shows_playoff_generation_readiness():
    assert "Slutspel redo att genereras" in SCHEDULE
    assert "Slutspel kan inte genereras" in SCHEDULE
