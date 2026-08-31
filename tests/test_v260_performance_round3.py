from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
ADMIN_OVERVIEW=(ROOT/"cupnavi_core/admin_overview.py").read_text(encoding="utf-8")


def test_admin_overview_flow_snapshot_is_reused_for_workflow_counts():
    start=APP.index('if _flow_index is not None:')
    end=APP.index('# Sidornas egna rubriker', start)
    block=APP[start:end]
    assert 'if admin_page == "Adminöversikt":' in block
    assert '("admin-workflow-counts", int(tid))' in block
    assert 'upcoming_n' in block and 'delayed_n' in block and 'pitches_n' in block


def test_admin_overview_does_not_fetch_all_matches_for_control_center():
    start=APP.index('elif admin_page == "Adminöversikt":')
    end=APP.index('if admin_page == "Cupinställningar":', start)
    block=APP[start:end]
    assert '_cc_matches = [dict(r) for r in all_rows(' not in block
    assert "build_control_status(" not in block
    assert "show_overview_advanced" in block
    assert "pitches=_count(counts, \"pitches_n\")" in ADMIN_OVERVIEW


def test_instruction_counts_are_batched():
    start=APP.index('if admin_page == "Instruktioner":')
    end=APP.index('elif admin_page == "Adminöversikt":', start)
    block=APP[start:end]
    assert 'guide_scheduled = guide_counts["scheduled_n"]' in block
    assert 'guide_published = guide_counts["published_n"]' in block
    assert 'guide_events = guide_counts["events_n"]' in block
    assert 'SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL' not in block
    assert 'WHERE m.tournament_id=?\n             AND (s.goals>0' not in block


def test_schedule_validation_bulk_loads_teams():
    start=APP.index('def validate_schedule(')
    end=APP.index('\n\ndef render_bracket_tree', start)
    block=APP[start:end]
    assert 'validation_teams = {int(r["id"]): r for r in all_rows("SELECT * FROM teams WHERE tournament_id=?"' in block
    assert 'home_team, away_team = validation_team(home_id), validation_team(away_id)' in block
    assert '= team(team_id)' not in block


def test_secondary_admin_page_schedule_status_comes_from_rules_snapshot():
    region=APP[APP.index('sidebar_rules = one_row('):APP.index('validation_cache_key =', APP.index('sidebar_rules = one_row('))]
    assert 'AS scheduled_n' in region
    assert 'sidebar_scheduled = _flow_scheduled if _flow_index is not None else' in region
