from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
VERSION=(ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()

def test_v345_version_sync():
    assert VERSION == '2026.08.31-347-SCHEDULE-READINESS-POLISH'
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert f'APP_VERSION = "{VERSION}"' in (ROOT/'cupnavi_core/version.py').read_text(encoding='utf-8')

def test_flow_counts_track_unassigned_teams():
    assert APP.count('AS unassigned_n') >= 2
    assert '_journey_unassigned_n = int(_flow_counts["unassigned_n"] or 0)' in APP

def test_expected_team_count_blocks_premature_group_recommendation():
    assert '_journey_expected_n = int(tournament["expected_team_count"] or 0)' in APP
    assert '_journey_teams_ready = _journey_teams_n > 0 and (not _journey_expected_n or _journey_teams_n >= _journey_expected_n)' in APP
    assert 'f"Lägg till lag ({_journey_teams_n}/{_journey_expected_n})"' in APP

def test_unassigned_teams_block_premature_schedule_recommendation():
    assert 'elif _journey_unassigned_n > 0:' in APP
    assert '"Grupper", f"Placera' in APP
    assert "Schema blir nästa steg när alla lag är placerade." in APP

def test_no_schema_or_database_contract_change():
    assert 'ALTER TABLE' not in APP[APP.index('if _flow_index is not None:'):APP.index('current_schedule_dirty =')]
