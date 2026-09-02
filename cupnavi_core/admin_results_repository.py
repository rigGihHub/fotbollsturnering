"""Read-only queries for the admin results workspace."""


def fetch_admin_results_matches(all_rows, tournament_id):
    """Load the match list first; auxiliary data can wait until an editor is needed."""
    return all_rows(
        "SELECT * FROM matches WHERE tournament_id=? ORDER BY CASE stage WHEN 'Gruppspel' THEN 0 ELSE 1 END, group_id, bracket_id, round_no, match_no",
        (tournament_id,),
    )


def fetch_admin_results_auxiliary(all_rows, tournament_id):
    """Load referees and team names only when playable matches need an editor."""
    referees = all_rows("SELECT * FROM referees WHERE tournament_id=? ORDER BY name", (tournament_id,))
    teams = all_rows("SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))
    return referees, teams


def fetch_admin_results_data(all_rows, tournament_id):
    """Compatibility wrapper for callers that still want the complete snapshot."""
    matches = fetch_admin_results_matches(all_rows, tournament_id)
    referees, teams = fetch_admin_results_auxiliary(all_rows, tournament_id)
    return matches, referees, teams
