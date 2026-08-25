from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def _block(start_name, end_name):
    start=APP.index(start_name)
    end=APP.index(end_name,start)
    return APP[start:end]

def test_statistics_and_info_are_streamlit_fragments():
    stats_prefix=APP[APP.index("@st.fragment\ndef render_public_statistics_section")-1:]
    assert "@st.fragment\ndef render_public_statistics_section" in APP
    assert "@st.fragment\ndef render_public_info_section" in APP

def test_main_public_renderer_delegates_heavy_sections():
    public=_block("def render_public_view(", "def render_match_reporter_view(")
    assert "render_public_statistics_section(" in public
    assert 'forced_section=tr("Tabeller")' in public
    assert 'forced_section=tr("Slutspel")' in public
    assert 'forced_section=tr("Topplistor")' in public
    assert "render_public_info_section(tournament_id, tournament, published_matches)" in public
    # Screen mode intentionally keeps a tiny LIMIT 8 sponsor query.
    assert 'SELECT * FROM offers WHERE tournament_id=?' not in public
    assert 'SELECT * FROM functionaries' not in public
    assert 'FROM player_match_stats s JOIN players' not in public

def test_statistics_queries_are_branch_local():
    stats=_block("def render_public_statistics_section(", "def render_public_info_section(")
    top=stats.index('if stats_section == tr("Topplistor") and _has_toplists:')
    query=stats.index("FROM player_match_stats s JOIN players")
    assert query > top
    assert 'if stats_section == tr("Slutspel"):' in stats

def test_info_queries_are_isolated_from_matches_and_statistics():
    info=_block("def render_public_info_section(", "def render_public_view(")
    assert "SELECT * FROM functionaries" in info
    assert "SELECT * FROM offers" in info
    assert "SELECT * FROM sponsors" in info
    assert "public_feedback_" in info

def test_info_summary_teams_are_loaded_only_for_completed_summary():
    info=_block("def render_public_info_section(", "def render_public_view(")
    condition=info.index("if all_public_matches and all(")
    teams_query=info.index('summary_teams = all_rows("SELECT * FROM teams')
    assert teams_query > condition
