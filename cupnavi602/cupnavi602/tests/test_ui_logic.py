import unittest
from cupnavi_core.ui_logic import match_belongs_to_team, schedule_issue_labels

class PublicTeamFilterTests(unittest.TestCase):
    def test_all_teams_when_no_filter(self):
        self.assertTrue(match_belongs_to_team(1, 2, None))

    def test_home_team_matches_filter(self):
        self.assertTrue(match_belongs_to_team(5, 9, 5))

    def test_away_team_matches_filter(self):
        self.assertTrue(match_belongs_to_team(5, 9, 9))

    def test_unrelated_team_is_filtered_out(self):
        self.assertFalse(match_belongs_to_team(5, 9, 7))

class ScheduleIssueTests(unittest.TestCase):
    def test_no_issues(self):
        self.assertEqual(schedule_issue_labels(), [])

    def test_combined_issues(self):
        self.assertEqual(
            schedule_issue_labels(referee_missing=True, color_conflict=True),
            ["Domare saknas", "Färgkrock"],
        )

if __name__ == "__main__":
    unittest.main()
