from pathlib import Path


def _statistics_source():
    return Path("cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")


def test_goal_leaderboards_exclude_zero_goals():
    text = _statistics_source()
    assert 'SUM(COALESCE(s.goals,0)) > 0' in text
    assert 'if r["goals"] > 0' in text


def test_assist_leaderboards_exclude_zero_assists():
    text = _statistics_source()
    assert 'SUM(COALESCE(s.assists,0)) > 0' in text
    assert 'if r["assists"] > 0' in text


def test_ranking_is_numbered_after_filtering():
    text = (Path("app.py").read_text(encoding="utf-8") + _statistics_source())
    assert 'for i, r in enumerate(goal_rows, 1)' in text
    assert 'for i, r in enumerate(assist_rows, 1)' in text
