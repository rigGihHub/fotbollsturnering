from pathlib import Path

VERSION = "2026.09.03-423-PUBLIC-INFO-COLD-START"


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
    assert block.count('SELECT * FROM teams WHERE tournament_id=? ORDER BY name') == 1
    assert 'edit_class_rows = class_rows' in block
    assert block.count('competition_classes(tid)') == 1  # sync_competition_classes only contains the token as suffix


def test_group_page_reuses_group_rows_for_count_and_rendering():
    app = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    start = app.index('if admin_page == "Grupper":')
    end = app.index('if admin_page == "Trupper":', start)
    block = app[start:end]
    assert '_existing_groups_count = len(groups)' in block
    assert block.count('SELECT * FROM groups WHERE tournament_id=? ORDER BY name') == 1
    assert 'SELECT COUNT(*) AS n FROM groups WHERE tournament_id=?' in block  # freshness check exists only inside the create transaction
