from pathlib import Path

from cupnavi_core.demo_data_service import DemoDataDeps, DemoDataService

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SERVICE = (ROOT / "cupnavi_core" / "demo_data_service.py").read_text(encoding="utf-8")
VERSION = "2026.08.29-302-PUBLIC-MATCH-EVENT-ROBUSTNESS"


def _noop(*args, **kwargs):
    return None


def _deps(**overrides):
    defaults = dict(
        all_rows=lambda *a, **k: [],
        one_row=lambda *a, **k: None,
        run=_noop,
        db=_noop,
        resolve_source=lambda value: value,
        clear_render_query_cache=_noop,
        is_test_environment=lambda row: False,
        ensure_tournament_day_windows=_noop,
        ensure_pitch_day_windows=_noop,
        create_all_group_matches=_noop,
        ensure_playoffs_for_schedule=lambda *a, **k: (True, None),
        generate_schedule=lambda *a, **k: (0, 0, None),
        add_feed_item=_noop,
        rows_from_cursor=lambda cursor: [],
    )
    defaults.update(overrides)
    return DemoDataDeps(**defaults)


def test_v278_version_contract():
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert f'APP_VERSION = "{VERSION}"' in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_demo_engine_is_outside_app_and_wrappers_delegate():
    assert "class DemoDataService" in SERVICE
    assert "DemoDataDeps(" in APP
    assert "return _demo_data_service().apply_progress_level(tournament_id, level)" in APP
    assert "UPDATE matches SET home_score=NULL" not in APP
    assert "UPDATE matches SET home_score=NULL" in SERVICE


def test_distribute_count_preserves_total_and_known_player_ids(monkeypatch):
    service = DemoDataService(_deps())
    players = [{"id": 11}, {"id": 12}]
    monkeypatch.setattr("cupnavi_core.demo_data_service.random.choice", lambda rows: rows[0])
    assert service.distribute_count(4, players) == {11: 4}
    assert service.distribute_count(0, players) == {}
    assert service.distribute_count(3, []) == {}


def test_safe_capacity_never_mutates_real_tournament():
    calls = []
    expected = {"pitch_count": 2}
    deps = _deps(
        one_row=lambda sql, params: expected,
        run=lambda *a, **k: calls.append((a, k)),
        is_test_environment=lambda row: False,
    )
    result = DemoDataService(deps).apply_safe_schedule_capacity(7, {"environment": "production"})
    assert result is expected
    assert calls == []


def test_prepare_schedule_retries_only_for_test_environment():
    generated = []
    rules = {"pitch_count": 1, "first_match_time": "09:00", "latest_kickoff_time": "18:00"}
    tournament = {"id": 3}
    one_rows = iter([tournament, rules])

    def one_row(sql, params):
        try:
            return next(one_rows)
        except StopIteration:
            return rules

    def generate(*args):
        generated.append(args)
        return (2, 1, "kapacitetsvarning")

    service = DemoDataService(_deps(one_row=one_row, generate_schedule=generate, is_test_environment=lambda row: False))
    ok, warning = service.prepare_schedule(3)
    assert ok is False
    assert warning == "kapacitetsvarning"
    assert len(generated) == 1
