from pathlib import Path
from cupnavi_core.playoff_dependency_safety import transitive_downstream_match_ids

VERSION = "2026.09.07-507-REVIEWED-DOCUMENT-SCHEDULE-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")


def _value(row, key, default=None):
    return row.get(key, default)


def test_version_is_v478():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_chain_finds_semifinal_and_final():
    rows = [
        {"id": 10, "home_source": "team:1", "away_source": "team:2"},
        {"id": 20, "home_source": "winner:10", "away_source": "team:3"},
        {"id": 30, "home_source": "winner:20", "away_source": "team:4"},
    ]
    assert transitive_downstream_match_ids(10, rows, row_value=_value) == (20, 30)


def test_chain_follows_loser_path():
    rows = [
        {"id": 10, "home_source": "team:1", "away_source": "team:2"},
        {"id": 21, "home_source": "loser:10", "away_source": "team:3"},
        {"id": 31, "home_source": "winner:21", "away_source": "team:4"},
    ]
    assert transitive_downstream_match_ids(10, rows, row_value=_value) == (21, 31)


def test_chain_is_cycle_safe():
    rows = [
        {"id": 10, "home_source": "winner:30", "away_source": "team:2"},
        {"id": 20, "home_source": "winner:10", "away_source": "team:3"},
        {"id": 30, "home_source": "winner:20", "away_source": "team:4"},
    ]
    assert transitive_downstream_match_ids(10, rows, row_value=_value) == (20, 30)


def test_unrelated_matches_are_ignored():
    rows = [
        {"id": 10, "home_source": "team:1", "away_source": "team:2"},
        {"id": 20, "home_source": "winner:10", "away_source": "team:3"},
        {"id": 99, "home_source": "team:8", "away_source": "team:9"},
    ]
    assert transitive_downstream_match_ids(10, rows, row_value=_value) == (20,)


def test_guard_uses_same_bracket_snapshot_and_transitive_ids():
    start = APP.index("def _playoff_dependency_guard(")
    end = APP.index("def _reset_unused_playoff_downstream_match(", start)
    block = APP[start:end]
    assert "WHERE m.bracket_id=?" in block
    assert "transitive_downstream_match_ids(" in block
    assert "descendant_ids = set(" in block
    assert "downstream_rows = [" in block


def test_guard_still_checks_locked_descendants():
    start = APP.index("def _playoff_dependency_guard(")
    end = APP.index("def _reset_unused_playoff_downstream_match(", start)
    block = APP[start:end]
    assert "dependency_impact(" in block
    assert "build_dependency_guidance(" in block
