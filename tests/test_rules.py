import unittest
from cupnavi_core.rules import (
    validate_match_event_totals,
    round_robin_match_count,
    playoff_extra_minutes,
)

class MatchEventRulesTests(unittest.TestCase):
    def test_goals_may_equal_team_score(self):
        self.assertTrue(validate_match_event_totals(3, 3, 2)["ok"])

    def test_player_goals_cannot_exceed_team_score(self):
        result = validate_match_event_totals(2, 3, 1)
        self.assertFalse(result["ok"])

    def test_assists_cannot_exceed_team_score(self):
        result = validate_match_event_totals(1, 1, 2)
        self.assertFalse(result["ok"])

    def test_assists_do_not_need_to_equal_goals(self):
        self.assertTrue(validate_match_event_totals(4, 4, 0)["ok"])

class SchedulingRulesTests(unittest.TestCase):
    def test_round_robin_eight_teams(self):
        self.assertEqual(round_robin_match_count(8), 28)

    def test_round_robin_four_teams(self):
        self.assertEqual(round_robin_match_count(4), 6)

    def test_extra_time_only_when_selected(self):
        self.assertEqual(playoff_extra_minutes("Förlängning + straffar", 10), 10)
        self.assertEqual(playoff_extra_minutes("Straffar direkt", 10), 0)
        self.assertEqual(playoff_extra_minutes("Lottning", 10), 0)

if __name__ == "__main__":
    unittest.main()
