"""Read-only data access for the restricted participant/team portal."""


def fetch_portal_teams(all_rows, tournament_id):
    return all_rows("SELECT * FROM teams WHERE tournament_id=? ORDER BY name", (tournament_id,))


def fetch_portal_credential(one_row, tournament_id, team_id):
    return one_row(
        "SELECT * FROM participant_access_credentials WHERE tournament_id=? AND team_id=?",
        (tournament_id, team_id),
    )


def fetch_received_messages(all_rows, tournament_id, team_id):
    return all_rows(
        """SELECT * FROM team_messages
           WHERE tournament_id=? AND recipient_type='team' AND recipient_team_id=?
           ORDER BY created_at DESC,id DESC LIMIT 200""",
        (tournament_id, team_id),
    )


def fetch_sent_messages(all_rows, tournament_id, team_id):
    return all_rows(
        """SELECT * FROM team_messages
           WHERE tournament_id=? AND sender_type='team' AND sender_team_id=?
           ORDER BY created_at DESC,id DESC LIMIT 200""",
        (tournament_id, team_id),
    )


def fetch_portal_matches(all_rows, tournament_id, team_id, match_team_ids, *, order_by_pitch=False):
    direct_team_source = f"team:{int(team_id)}"
    order_clause = "scheduled_start,pitch_number,id" if order_by_pitch else "scheduled_start,id"
    rows = all_rows(
        f"""SELECT * FROM matches
            WHERE tournament_id=? AND scheduled_start IS NOT NULL
              AND (home_source=? OR away_source=? OR home_source NOT LIKE 'team:%' OR away_source NOT LIKE 'team:%')
            ORDER BY {order_clause}""",
        (tournament_id, direct_team_source, direct_team_source),
    )
    return [row for row in rows if int(team_id) in match_team_ids(row)]


def fetch_team_players(all_rows, team_id):
    return all_rows("SELECT * FROM players WHERE team_id=? ORDER BY player_number,name", (team_id,))


def fetch_match_rosters(all_rows, team_id):
    return all_rows(
        """SELECT match_id,player_id
           FROM match_rosters
           WHERE team_id=?
           ORDER BY match_id,player_id""",
        (team_id,),
    )
