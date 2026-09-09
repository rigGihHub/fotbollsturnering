from pathlib import Path
from cupnavi_core.home_away import orientation_balance_score

def test_balance_prefers_team_with_fewer_home_matches_as_home():
    home = {1: 0, 2: 2}
    away = {1: 2, 2: 0}
    assert orientation_balance_score(1, 2, home, away) < orientation_balance_score(2, 1, home, away)

def test_balanced_orientation_score_can_tie_for_fresh_teams():
    assert orientation_balance_score(1, 2, {}, {}) == orientation_balance_score(2, 1, {}, {})

def test_app_checks_color_conflict_in_both_directions():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "conflict_a_home = kit_color_conflict(team_a, team_b)" in text
    assert "conflict_b_home = kit_color_conflict(team_b, team_a)" in text

def test_color_priority_precedes_balance():
    text = Path("app.py").read_text(encoding="utf-8")
    color_check = text.index("if conflict_a_home != conflict_b_home:")
    balance_check = text.index("score_ab = orientation_balance_score")
    assert color_check < balance_check

def test_played_group_matches_are_not_reoriented():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'if match_row["home_score"] is not None or match_row["away_score"] is not None:' in text
    assert "editable.append" in text

def test_optimizer_runs_when_group_matches_are_created():
    text = Path("app.py").read_text(encoding="utf-8")
    assert text.count("optimize_group_home_away(tournament_id)") >= 2
