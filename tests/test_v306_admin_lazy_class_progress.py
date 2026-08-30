from pathlib import Path

APP = Path('app.py').read_text()
VERSION = Path('VERSION.txt').read_text().strip()


def _overview_block():
    start = APP.index('elif admin_page == "Adminöversikt":')
    end = APP.index('if admin_page == "Cupinställningar":', start)
    return APP[start:end]


def test_release_version_is_v306():
    assert VERSION == '2026.08.30-320-PUBLIC-PLAYOFF-TEAM-BATCHING'
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP


def test_class_progress_query_is_user_gated():
    block = _overview_block()
    toggle = block.index('"Visa lagfördelning per klass"')
    gate = block.index('if _show_class_progress:', toggle)
    query = block.index('SELECT competition_class_id, COUNT(*) AS n', gate)
    assert toggle < gate < query


def test_class_progress_detail_remains_available():
    block = _overview_block()
    assert 'class_progress_caption(_v139_class_rows, _class_team_counts, competition_class_label)' in block
    assert 'admin_overview_class_progress_{tid}' in block
