from pathlib import Path

VERSION = "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_version_and_release_note():
    root = Path(__file__).resolve().parents[1]
    assert (root / "VERSION.txt").read_text().strip() == VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in (root / "app.py").read_text()
    assert (root / "ADMIN_CORE_QUERY_REUSE_V397.md").exists()


def test_team_page_reuses_team_and_class_reads():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    start = app.index('if admin_page == "Lag":')
    end = app.index('if admin_page == "Grupper":', start)
    block = app[start:end]
    assert 'registered_team_count = len(teams)' in block
    assert block.count('admin_teams_snapshot(tid)') == 1
    assert 'edit_class_rows = class_rows' in block
    assert block.count('admin_classes_snapshot(tid)') == 1


def test_group_page_reuses_group_rows_for_count_and_rendering():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    start = app.index('if admin_page == "Grupper":')
    end = app.index('if admin_page == "Trupper":', start)
    block = app[start:end]
    assert '_existing_groups_count = len(groups)' in block
    assert block.count('admin_groups_snapshot(tid)') == 1
    assert 'SELECT COUNT(*) AS n FROM groups WHERE tournament_id=?' in block  # freshness check exists only inside the create transaction
