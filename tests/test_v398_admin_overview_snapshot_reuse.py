from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')
VERSION = Path('VERSION.txt').read_text(encoding='utf-8').strip()


def _overview_section():
    start = APP.index('elif admin_page == "Adminöversikt":')
    end = APP.index('\nif admin_page == "Cupinställningar":', start)
    return APP[start:end]


def test_release_version():
    assert VERSION == '2026.09.03-423-PUBLIC-INFO-COLD-START'


def test_control_center_reuses_unchecked_snapshot_count():
    section = _overview_section()
    assert 'unchecked = int(workflow_counts["unchecked_n"] or 0)' in section
    assert 'SELECT COUNT(*) AS n FROM teams WHERE tournament_id=? AND COALESCE(checked_in,0)=0' not in section


def test_direct_edit_reuses_team_and_played_counts():
    section = _overview_section()
    assert 'current_team_count_for_limit = teams_n' in section
    assert '_prod_history_locked = (not is_test_environment(tournament)) and played_n > 0' in section


def test_start_control_uses_counts_not_full_table_reads():
    section = _overview_section()
    marker = 'if _show_start_control:'
    start = section.index(marker)
    end = section.index('with st.expander("⚠️ Riskzon', start)
    start_control = section[start:end]
    assert 'workflow_counts["scheduled_n"]' in start_control
    assert 'workflow_counts["missing_refs_n"]' in start_control
    assert 'workflow_counts["published_n"]' in start_control
    assert 'SELECT * FROM groups WHERE tournament_id=?' not in start_control
    assert 'SELECT * FROM teams WHERE tournament_id=?' not in start_control
    assert 'SELECT * FROM matches WHERE tournament_id=?' not in start_control
