"""Read-only public repository for the standalone CupNavi API.

Uses the same Turso environment names as the Streamlit application:
TURSO_DATABASE_URL and TURSO_AUTH_TOKEN. If they are absent, local SQLite is used.
"""
from __future__ import annotations
import os, sqlite3
from contextlib import contextmanager

PUBLIC_TOURNAMENT_FIELDS = (
    "id","name","public_slug","sport","start_date","end_date","organizer","arena_address",
    "arrangement_type","results_counted",
    "kiosk_available","kiosk_information","public_information","organizer_phone",
    "feedback_email","instagram_url","playoff_format","bronze_match","points_win",
    "points_draw","points_loss","table_tiebreak","show_scorer_stats","show_assist_stats",
    "show_card_stats","show_fairness","show_public_weather","show_public_kits","show_public_away_kits","show_public_logos","enable_team_checkin","is_published",
    "halves","minutes_per_half","halftime_minutes","pitch_break_minutes","minimum_team_rest_minutes","avoid_consecutive_matches","consecutive_match_break_minutes",
    "organizer_phone","feedback_email","instagram_url","playoff_format","bronze_match",
)

def backend_name() -> str:
    return "turso" if os.getenv("TURSO_DATABASE_URL") and os.getenv("TURSO_AUTH_TOKEN") else "sqlite"

def database_probe():
    """Small read-only probe used by /health; does not expose secrets or schema content."""
    import time
    started=time.perf_counter()
    try:
        row=one("SELECT 1 AS ok")
        ok=bool(row and int(row.get("ok",0))==1)
        error=None
    except Exception as exc:
        ok=False
        error=type(exc).__name__
    return {
        "ok":ok,
        "latency_ms":round((time.perf_counter()-started)*1000,1),
        "error":error,
    }

def _database_path() -> str:
    return os.getenv("CUPNAVI_API_SQLITE_PATH", "turnering.db")

@contextmanager
def connect():
    """Open a read connection using Turso when configured, otherwise SQLite."""
    if backend_name()=="turso":
        try:
            import libsql
        except ImportError as exc:
            raise RuntimeError("Turso is configured but the libsql package is unavailable.") from exc
        con=libsql.connect(
            database=os.environ["TURSO_DATABASE_URL"],
            auth_token=os.environ["TURSO_AUTH_TOKEN"],
        )
    else:
        con=sqlite3.connect(_database_path())
        con.row_factory=sqlite3.Row
    try:
        yield con
    finally:
        con.close()

def _dict_rows(cursor):
    rows=cursor.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], sqlite3.Row):
        return [dict(r) for r in rows]
    columns=[item[0] for item in (cursor.description or [])]
    if columns:
        return [dict(zip(columns,row)) for row in rows]
    if isinstance(rows[0],dict):
        return [dict(r) for r in rows]
    raise RuntimeError("Unsupported database row format.")

def one(sql, params=()):
    with connect() as con:
        cursor=con.execute(sql,params)
        rows=_dict_rows(cursor)
        return rows[0] if rows else None

def all_rows(sql, params=()):
    with connect() as con:
        return _dict_rows(con.execute(sql,params))

def _public_tournament_projection(row):
    if not row:
        return None
    return {key:row.get(key) for key in PUBLIC_TOURNAMENT_FIELDS if key in row}

def public_tournament(public_key):
    row=one("SELECT * FROM tournaments WHERE public_slug=? AND is_published=1",(str(public_key),))
    if not row:
        try:
            row=one("SELECT * FROM tournaments WHERE id=? AND is_published=1",(int(public_key),))
        except (TypeError,ValueError):
            row=None
    return _public_tournament_projection(row)

def public_teams(tournament_id):
    columns={str(row.get("name")) for row in all_rows("PRAGMA table_info(teams)")}
    kit_projection=("home_pattern,home_color_2,away_pattern,away_color_2" if
                    {"home_pattern","home_color_2","away_pattern","away_color_2"}.issubset(columns) else
                    "'Helfärgad' AS home_pattern,'#FFFFFF' AS home_color_2,'Helfärgad' AS away_pattern,'#111827' AS away_color_2")
    logo_projection=("logo_url,logo_source_url" if {"logo_url","logo_source_url"}.issubset(columns) else "NULL AS logo_url,NULL AS logo_source_url")
    return all_rows(
        f"""SELECT id,name,group_id,age_class,primary_color,secondary_color,{kit_projection},{logo_projection}
            FROM teams WHERE tournament_id=? ORDER BY name""",
        (int(tournament_id),),
    )

def public_groups(tournament_id):
    return all_rows(
        "SELECT id,name,age_class FROM groups WHERE tournament_id=? ORDER BY name",
        (int(tournament_id),),
    )

def public_matches(tournament_id):
    return all_rows(
        """SELECT id,stage,group_id,bracket_id,round_no,match_no,home_source,away_source,
                  scheduled_start,pitch_number,home_score,away_score,home_penalties,away_penalties,
                  decided_winner_id,schedule_published,match_status,status_updated_at,
                  actual_started_at,actual_finished_at
           FROM matches
           WHERE tournament_id=? AND schedule_published=1 AND scheduled_start IS NOT NULL
           ORDER BY scheduled_start,pitch_number,id""",
        (int(tournament_id),),
    )

def public_venue_points(tournament_id):
    return all_rows(
        """SELECT id,kind,label,detail,url FROM venue_points
           WHERE tournament_id=? ORDER BY label,id""",
        (int(tournament_id),),
    )

def public_notifications(tournament_id,team_id):
    return all_rows(
        """SELECT id,team_id,created_at,title,message
           FROM notifications
           WHERE tournament_id=? AND (team_id=? OR team_id IS NULL)
           ORDER BY created_at DESC,id DESC LIMIT 20""",
        (int(tournament_id),int(team_id)),
    )

def public_statistics(tournament_id):
    """Return public player/team leaderboards from registered match events.

    Uses only persisted player_match_stats. No score-derived or synthetic player events
    are invented when a goal has not been assigned to a player.
    """
    tid=int(tournament_id)
    rows=all_rows(
        """SELECT p.id AS player_id,p.name AS player_name,p.player_number,
                  t.id AS team_id,t.name AS team_name,
                  COALESCE(SUM(pms.goals),0) AS goals,
                  COALESCE(SUM(pms.assists),0) AS assists,
                  COALESCE(SUM(pms.yellow_cards),0) AS yellow_cards,
                  COALESCE(SUM(pms.red_cards),0) AS red_cards
           FROM player_match_stats pms
           JOIN matches m ON m.id=pms.match_id
           JOIN players p ON p.id=pms.player_id
           JOIN teams t ON t.id=p.team_id
           WHERE m.tournament_id=?
           GROUP BY p.id,p.name,p.player_number,t.id,t.name""",
        (tid,),
    )
    normalized=[]
    for row in rows:
        item=dict(row)
        for key in ("goals","assists","yellow_cards","red_cards"):
            item[key]=int(item.get(key) or 0)
        normalized.append(item)

    def ranked(metric):
        return sorted(
            [row for row in normalized if int(row.get(metric) or 0)>0],
            key=lambda row:(-int(row.get(metric) or 0),str(row.get("player_name") or "").casefold()),
        )

    team_cards={}
    for row in normalized:
        team_id=int(row["team_id"])
        bucket=team_cards.setdefault(team_id,{"team_id":team_id,"team_name":row["team_name"],"yellow_cards":0,"red_cards":0})
        bucket["yellow_cards"]+=int(row["yellow_cards"])
        bucket["red_cards"]+=int(row["red_cards"])

    discipline=sorted(
        team_cards.values(),
        key=lambda row:(int(row["red_cards"]),int(row["yellow_cards"]),str(row["team_name"]).casefold()),
    )
    return {
        "scorers":ranked("goals"),
        "assists":ranked("assists"),
        "cards":sorted(
            [row for row in normalized if int(row["yellow_cards"])+int(row["red_cards"])>0],
            key=lambda row:(-int(row["red_cards"]),-int(row["yellow_cards"]),str(row["player_name"]).casefold()),
        ),
        "discipline":discipline,
    }

def group_teams(group_id):
    return all_rows(
        "SELECT id,name,group_id FROM teams WHERE group_id=? ORDER BY name",
        (int(group_id),),
    )

def group_completed_matches(group_id):
    return all_rows(
        """SELECT home_source,away_source,home_score,away_score
           FROM matches
           WHERE group_id=? AND stage='Gruppspel'
             AND home_score IS NOT NULL AND away_score IS NOT NULL""",
        (int(group_id),),
    )

def standings_inputs(tournament_id):
    """Batch-load all standings input in three queries regardless of group count."""
    tid=int(tournament_id)
    groups=public_groups(tid)
    teams=all_rows(
        "SELECT id,name,group_id FROM teams WHERE tournament_id=? ORDER BY name",
        (tid,),
    )
    matches=all_rows(
        """SELECT group_id,home_source,away_source,home_score,away_score
           FROM matches
           WHERE tournament_id=? AND stage='Gruppspel'
             AND home_score IS NOT NULL AND away_score IS NOT NULL""",
        (tid,),
    )
    teams_by_group={}
    for row in teams:
        teams_by_group.setdefault(row.get("group_id"),[]).append(row)
    matches_by_group={}
    for row in matches:
        matches_by_group.setdefault(row.get("group_id"),[]).append(row)
    return groups,teams_by_group,matches_by_group

def public_brackets(tournament_id):
    """Load every bracket and its matches in two queries instead of one query per bracket."""
    tid=int(tournament_id)
    brackets=all_rows(
        "SELECT id,name,size,bronze_match FROM brackets WHERE tournament_id=? ORDER BY id",
        (tid,),
    )
    if not brackets:
        return []
    matches=all_rows(
        """SELECT id,bracket_id,stage,round_no,match_no,home_source,away_source,scheduled_start,pitch_number,
                  home_score,away_score,home_penalties,away_penalties,decided_winner_id,schedule_published,
                  match_status,status_updated_at,actual_started_at,actual_finished_at
           FROM matches
           WHERE tournament_id=? AND bracket_id IS NOT NULL AND schedule_published=1
           ORDER BY bracket_id,round_no,match_no,id""",
        (tid,),
    )
    by_bracket={}
    for row in matches:
        by_bracket.setdefault(int(row["bracket_id"]),[]).append(row)
    for bracket in brackets:
        bracket["matches"]=by_bracket.get(int(bracket["id"]),[])
    return brackets

def public_snapshot(public_key, *, include_unpublished=False):
    """Hydrate the public PWA snapshot with one database connection.

    This is intentionally uncached so live scores stay fresh; the optimization is
    connection reuse, not stale data.
    """
    with connect() as con:
        def many(sql, params=()):
            return _dict_rows(con.execute(sql, params))
        def first(sql, params=()):
            rows=many(sql, params)
            return rows[0] if rows else None

        publish_filter="" if include_unpublished else " AND is_published=1"
        row=first(f"SELECT * FROM tournaments WHERE public_slug=?{publish_filter}", (str(public_key),))
        if not row:
            try:
                row=first(f"SELECT * FROM tournaments WHERE id=?{publish_filter}", (int(public_key),))
            except (TypeError,ValueError):
                row=None
        tournament=_public_tournament_projection(row)
        if not tournament:
            return None
        tid=int(tournament["id"])
        team_columns={str(item.get("name")) for item in many("PRAGMA table_info(teams)")}
        kit_projection=("home_pattern,home_color_2,away_pattern,away_color_2" if
                        {"home_pattern","home_color_2","away_pattern","away_color_2"}.issubset(team_columns) else
                        "'Helfärgad' AS home_pattern,'#FFFFFF' AS home_color_2,'Helfärgad' AS away_pattern,'#111827' AS away_color_2")
        # Only include crest fields when the public presentation actually uses
        # them. Large external URLs are otherwise dead payload on every matchday load.
        wants_logos=bool(tournament.get("show_public_logos"))
        logo_projection=("logo_url,logo_source_url" if wants_logos and {"logo_url","logo_source_url"}.issubset(team_columns) else "NULL AS logo_url,NULL AS logo_source_url")
        teams=many(f"SELECT id,name,group_id,age_class,primary_color,secondary_color,{kit_projection},{logo_projection} FROM teams WHERE tournament_id=? ORDER BY name", (tid,))
        groups=many("SELECT id,name,age_class FROM groups WHERE tournament_id=? ORDER BY name", (tid,))
        match_publish_filter="" if include_unpublished else " AND schedule_published=1"
        matches=many(f"""SELECT id,stage,group_id,bracket_id,round_no,match_no,home_source,away_source,
                              scheduled_start,pitch_number,home_score,away_score,home_penalties,away_penalties,
                              decided_winner_id,schedule_published,match_status,status_updated_at,
                              actual_started_at,actual_finished_at
                       FROM matches WHERE tournament_id=?{match_publish_filter} AND scheduled_start IS NOT NULL
                       ORDER BY scheduled_start,pitch_number,id""", (tid,))
        venue_points=many("SELECT id,kind,label,detail,url FROM venue_points WHERE tournament_id=? ORDER BY label,id", (tid,))
        pitch_columns={str(item.get("name")) for item in many("PRAGMA table_info(pitches)")}
        pitch_optional=[name for name in ("opens_at","closes_at","start_time","end_time","available_from","available_to") if name in pitch_columns]
        pitch_select="pitch_number,name"+(" ,"+",".join(pitch_optional) if pitch_optional else "")
        pitches=many(f"SELECT {pitch_select} FROM pitches WHERE tournament_id=? ORDER BY pitch_number", (tid,))
        bracket_columns={str(item.get("name")) for item in many("PRAGMA table_info(brackets)")}
        bracket_extra=[name for name in ("qualification_rule","source_rule","group_positions","qualifying_positions") if name in bracket_columns]
        bracket_select="id,name,size,bronze_match"+(" ,"+",".join(bracket_extra) if bracket_extra else "")
        brackets=many(f"SELECT {bracket_select} FROM brackets WHERE tournament_id=? ORDER BY id", (tid,))
        if brackets:
            # Reuse the already-loaded public match rows instead of querying the
            # matches table a second time. This keeps first paint to one match query.
            by_bracket={}
            for match in matches:
                if match.get("bracket_id") is not None:
                    by_bracket.setdefault(int(match["bracket_id"]),[]).append(dict(match))
            for bracket in brackets:
                bracket["matches"]=sorted(by_bracket.get(int(bracket["id"]),[]),key=lambda item:(int(item.get("round_no") or 0),int(item.get("match_no") or 0),int(item.get("id") or 0)))
        return {
            "tournament":tournament,
            "teams":teams,
            "groups":groups,
            "matches":matches,
            "brackets":brackets,
            "venue_points":venue_points,
            "pitches":pitches,
        }
