from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_release_version_is_v308():
    assert VERSION == '2026.08.30-320-PUBLIC-PLAYOFF-TEAM-BATCHING'


def test_direct_edit_is_opt_in_before_queries():
    toggle = APP.index('"Visa direktredigering av cupinställningar"')
    guard = APP.index('if show_direct_edit:', toggle)
    rules_query = APP.index('overview_rules = one_row("SELECT * FROM schedule_rules', guard)
    team_count = APP.index('current_team_count_for_limit = one_row("SELECT COUNT(*) AS n FROM teams', guard)
    assert toggle < guard < rules_query < team_count


def test_existing_direct_edit_section_remains_available():
    assert 'with st.expander("Direktredigera cupinställningar", expanded=True):' in APP
    assert '"Återställ sportens standardregler"' in APP
