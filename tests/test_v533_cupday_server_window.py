import ast
import datetime as dt
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_TEXT = (ROOT / "app.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")
MATCHES_VIEW = (ROOT / "cupnavi_core" / "public_matches_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def _cupday_combined_sql() -> str:
    tree = ast.parse(APP_TEXT)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "_combined_sql" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            if "'feed' AS row_kind" in node.value.value and "public_stats" in node.value.value:
                return node.value.value
    raise AssertionError("v533 cup-day SQL not found")


def test_v533_version_and_cupday_gate():
    assert VERSION == "2026.09.08-533-CUPDAY-SERVER-WINDOW"
    assert "_cup_day" in WORKSPACE
    assert "(_future_cup or _cup_day)" in WORKSPACE
    assert '_requested_match_view == "all"' in WORKSPACE
    assert '_segmented_match_view == tr("Alla")' in WORKSPACE
    assert "match_window_start=_public_match_window_start" in WORKSPACE
    assert "match_window_end=_public_match_window_end" in WORKSPACE


def test_v533_keeps_feed_and_summary_exact_while_match_list_is_batched():
    assert '"feed_matches": list(feed_matches if feed_matches is not None else matches)' in APP_TEXT
    assert '"played_count": int(played_count) if played_count is not None else None' in APP_TEXT
    assert '"total_goals": int(total_goals) if total_goals is not None else None' in APP_TEXT
    assert "feed_matches=_public_feed_matches" in WORKSPACE
    assert "played_match_total=_published_played_total" in WORKSPACE
    assert "total_goals=_published_total_goals" in WORKSPACE
    assert "list(feed_matches) if feed_matches is not None else published_matches" in MATCHES_VIEW
    assert "summary_played_count" in MATCHES_VIEW
    assert "summary_total_goals" in MATCHES_VIEW


def test_v533_cupday_sql_returns_first_batch_feed_window_and_exact_aggregates():
    sql = _cupday_combined_sql()
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE matches(
            id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,bracket_id INTEGER,
            stage TEXT,round_no INTEGER,match_no INTEGER,home_source TEXT,away_source TEXT,
            home_score INTEGER,away_score INTEGER,home_penalties INTEGER,away_penalties INTEGER,
            referee_id INTEGER,schedule_published INTEGER,decided_winner_id INTEGER,
            scheduled_start TEXT,pitch_number INTEGER
        );
        CREATE TABLE referees(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT);
        CREATE TABLE teams(
            id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,name TEXT,age_class TEXT,
            primary_color TEXT,secondary_color TEXT,home_pattern TEXT,home_color_2 TEXT,
            away_pattern TEXT,away_color_2 TEXT
        );
        """
    )
    con.execute("INSERT INTO teams VALUES (1,1,1,'A','P14','#1','#2','','','','')")
    con.execute("INSERT INTO teams VALUES (2,1,1,'B','P14','#1','#2','','','','')")
    base = dt.datetime(2026, 9, 8, 8, 0)
    for i in range(30):
        start = base + dt.timedelta(minutes=20 * i)
        home_score = 1 if i < 5 else None
        away_score = 0 if i < 5 else None
        con.execute(
            "INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                i + 1,1,1,None,"Gruppspel",None,None,"team:1","team:2",
                home_score,away_score,None,None,None,1,None,start.isoformat(),1,
            ),
        )

    rows = con.execute(
        sql,
        (1, 12, "2026-09-08T10:00:00", "2026-09-08T14:00:00", 1),
    ).fetchall()
    by_kind = {}
    for row in rows:
        by_kind.setdefault(row["row_kind"], []).append(row)

    assert len(by_kind["match"]) == 12
    assert 1 <= len(by_kind["feed"]) <= 18
    assert len(by_kind["team"]) == 2
    assert by_kind["match"][0]["match_total"] == 30
    assert by_kind["match"][0]["played_count"] == 5
    assert by_kind["match"][0]["total_goals"] == 5
    assert min(row["scheduled_start"] for row in by_kind["feed"]) >= "2026-09-08T10:00:00"
    assert max(row["scheduled_start"] for row in by_kind["feed"]) <= "2026-09-08T14:00:00"
