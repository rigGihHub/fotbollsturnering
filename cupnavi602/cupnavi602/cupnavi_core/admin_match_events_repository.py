"""Read-only queries for the admin Matchhändelser workspace."""


def fetch_played_matches(all_rows, tournament_id):
    return all_rows(
        "SELECT * FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL ORDER BY id DESC",
        (tournament_id,),
    )


def fetch_team_players(all_rows, team_id):
    return all_rows(
        "SELECT * FROM players WHERE team_id=? ORDER BY player_number,name",
        (team_id,),
    )


def fetch_team_match_stats(all_rows, match_id, team_id):
    return all_rows(
        "SELECT * FROM player_match_stats WHERE match_id=? AND player_id IN (SELECT id FROM players WHERE team_id=?)",
        (match_id, team_id),
    )
