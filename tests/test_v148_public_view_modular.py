from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
INFO=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
STATS=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
WORKSPACE=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")

def _block(start_name, end_name):
    start=APP.index(start_name)
    end=APP.index(end_name,start)
    return APP[start:end]

def test_public_workspace_uses_one_outer_streamlit_fragment():
    assert "@st.fragment\ndef render_public_view" in APP
    assert "@st.fragment\ndef render_public_statistics_section" not in APP
    assert "@st.fragment\ndef render_public_info_section" not in APP

def test_main_public_renderer_delegates_heavy_sections():
    public=WORKSPACE
    assert "render_public_statistics_section(" in public
    assert 'forced_section=tr("Tabeller")' in public
    assert 'forced_section=tr("Slutspel")' in public
    assert 'forced_section=tr("Topplistor")' in public
    assert "render_public_info_section(" in public
    assert "load_published_matches=_load_info_published_matches" in public
    # Screen mode intentionally keeps a tiny LIMIT 8 sponsor query.
    assert 'SELECT * FROM offers WHERE tournament_id=?' not in public
    assert 'SELECT * FROM functionaries' not in public
    assert 'FROM player_match_stats s JOIN players' not in public

def test_statistics_queries_are_branch_local():
    stats=STATS
    top=stats.index('if stats_section == tr("Topplistor") and _has_toplists:')
    query=stats.index("FROM player_match_stats s JOIN players")
    assert query > top
    assert 'if stats_section == tr("Slutspel"):' in stats

def test_info_queries_are_isolated_from_matches_and_statistics():
    info=INFO
    assert "SELECT * FROM functionaries" in info
    assert "SELECT * FROM offers" in info
    assert "SELECT * FROM sponsors" in info
    assert "public_feedback_" in info

def test_info_summary_teams_are_loaded_only_for_completed_summary():
    info=INFO
    condition=info.index("if cup_is_complete:")
    teams_query=info.index('summary_teams = all_rows("SELECT * FROM teams')
    assert teams_query > condition
