from pathlib import Path

def test_goal_leaderboards_exclude_zero_goals():
    text = Path("app.py").read_text(encoding="utf-8")
    assert text.count('if int(r["goals"] or 0) > 0') >= 2

def test_assist_leaderboards_exclude_zero_assists():
    text = Path("app.py").read_text(encoding="utf-8")
    assert text.count('if int(r["assists"] or 0) > 0') >= 2

def test_ranking_is_numbered_after_filtering():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'for i, r in enumerate(goal_rows, 1)' in text
    assert 'for i, r in enumerate(assist_rows, 1)' in text
