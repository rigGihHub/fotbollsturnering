from cupnavi_core.go_live_readiness import build_go_live_readiness


def _stats(**overrides):
    base = {
        "teams": 8,
        "players": 80,
        "teams_without_players": 0,
        "matches": 20,
        "unscheduled_matches": 0,
        "unpublished_matches": 0,
        "testable_matches": 12,
        "reporter_codes": 1,
    }
    base.update(overrides)
    return base


def _build(**overrides):
    args = {
        "cloud_database_enabled": True,
        "schema_version": 32,
        "required_schema_version": 32,
        "missing_tables": [],
        "published": True,
        "schedule_dirty": False,
        "schedule_errors": [],
        "stats": _stats(),
    }
    args.update(overrides)
    return build_go_live_readiness(**args)


def test_ready_cup_has_no_blockers():
    readiness = _build()
    assert readiness.ready is True
    assert readiness.blockers == ()
    assert readiness.ok_count == len(readiness.items)


def test_local_database_blocks_go_live():
    readiness = _build(cloud_database_enabled=False)
    assert readiness.ready is False
    assert any(item.key == "database" for item in readiness.blockers)


def test_missing_reporter_code_blocks_go_live():
    readiness = _build(stats=_stats(reporter_codes=0))
    assert any(item.key == "reporter_code" for item in readiness.blockers)


def test_dirty_or_incomplete_schedule_blocks_go_live():
    readiness = _build(schedule_dirty=True, stats=_stats(unscheduled_matches=2))
    schedule = next(item for item in readiness.items if item.key == "schedule")
    assert schedule.state == "blocker"
    assert "inaktuellt" in schedule.detail
    assert "2 matcher" in schedule.detail


def test_unpublished_match_blocks_public_live_flow():
    readiness = _build(stats=_stats(unpublished_matches=1))
    publication = next(item for item in readiness.items if item.key == "publication")
    assert publication.state == "blocker"


def test_missing_rosters_warn_but_do_not_block_team_result_reporting():
    readiness = _build(stats=_stats(players=0, teams_without_players=8))
    rosters = next(item for item in readiness.items if item.key == "rosters")
    assert rosters.state == "warning"
    assert readiness.ready is True


def test_missing_schema_or_critical_tables_blocks_go_live():
    readiness = _build(schema_version=31, missing_tables=["player_match_stats"])
    schema = next(item for item in readiness.items if item.key == "schema")
    assert schema.state == "blocker"
    assert "player_match_stats" in schema.detail


def test_no_testable_group_match_blocks_rehearsal():
    readiness = _build(stats=_stats(testable_matches=0))
    rehearsal = next(item for item in readiness.items if item.key == "test_match")
    assert rehearsal.state == "blocker"
