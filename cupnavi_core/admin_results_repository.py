"""Read-only queries for the admin results workspace."""


def fetch_admin_results_data(all_rows, tournament_id):
    matches = all_rows(
        "SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage WHEN 'Gruppspel' THEN 0 ELSE 1 END, group_id, bracket_id, round_no, match_no",
        (tournament_id,),
    )
    referees = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tournament_id,))
    teams = all_rows("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))
    return matches, referees, teams
