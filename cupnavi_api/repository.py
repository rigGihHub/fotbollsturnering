"""Read-only public repository for the standalone CupNavi API.

Uses the same Turso environment names as the Streamlit application:
TURSO_DATABASE_URL and TURSO_AUTH_TOKEN. If they are absent, local SQLite is used.
"""
from __future__ import annotations
import os, sqlite3
from contextlib import contextmanager

PUBLIC_TOURNAMENT_FIELDS = (
    "id","name","public_slug","sport","start_date","end_date","organizer","arena_address",
    "kiosk_available","kiosk_information","public_information","organizer_phone",
    "feedback_email","instagram_url","playoff_format","bronze_match","points_win",
    "points_draw","points_loss","table_tiebreak","show_scorer_stats","show_assist_stats",
    "show_card_stats","show_fairness","enable_team_checkin","is_published",
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
    # libsql follows DB-API cursor.description for tuple rows.
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
    return all_rows(
        """SELECT id,name,group_id,age_class,primary_color,secondary_color
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
                  decided_winner_id,schedule_published
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
                  home_score,away_score,home_penalties,away_penalties,decided_winner_id,schedule_published
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

def public_snapshot(public_key):
    tournament=public_tournament(public_key)
    if not tournament:
        return None
    tid=int(tournament["id"])
    return {
        "tournament":tournament,
        "teams":public_teams(tid),
        "groups":public_groups(tid),
        "matches":public_matches(tid),
        "brackets":public_brackets(tid),
        "venue_points":public_venue_points(tid),
    }
