
import ast
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP_PATH=ROOT/"app.py"


class LocalDbFactory:
    def __init__(self,path): self.path=path
    def __call__(self):
        con=sqlite3.connect(self.path)
        con.row_factory=sqlite3.Row
        return con


def _row_value(row,key,default=None):
    try: value=row[key]
    except Exception: value=default
    return default if value is None and default is not None else value


def _team_value(row,key,default=None):
    return _row_value(row,key,default)


def _load(path):
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    names={
        "_admin_team_snapshot",
        "_admin_update_team_if_unchanged",
        "_admin_delete_team_if_unchanged",
        "_admin_group_snapshot",
        "_admin_update_group_if_unchanged",
        "_admin_delete_group_if_unchanged",
        "_set_schedule_request_status_if_current",
    }
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==names
    module=ast.Module(body=nodes,type_ignores=[])
    ast.fix_missing_locations(module)
    ns={
        "sqlite3":sqlite3,
        "db":LocalDbFactory(path),
        "_row_value":_row_value,
        "_team_value":_team_value,
        "_clear_render_query_cache":lambda:None,
    }
    exec(compile(module,str(APP_PATH),"exec"),ns)
    return ns


def _create(path):
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE teams(
        id INTEGER PRIMARY KEY,tournament_id INTEGER NOT NULL,name TEXT,
        primary_color TEXT,secondary_color TEXT,home_pattern TEXT,home_color_2 TEXT,
        away_pattern TEXT,away_color_2 TEXT,distance_km INTEGER,late_first_match INTEGER,
        earliest_first_time TEXT,travel_note TEXT,avoid_late_group_match INTEGER,
        responsible_name TEXT,responsible_phone TEXT,responsible_email TEXT,
        age_class TEXT,competition_class_id INTEGER,group_id INTEGER,kit_confirmed_at TEXT
    )""")
    con.execute("""CREATE TABLE groups(
        id INTEGER PRIMARY KEY,tournament_id INTEGER NOT NULL,name TEXT,
        age_class TEXT,competition_class_id INTEGER
    )""")
    con.execute("""CREATE TABLE matches(
        id INTEGER PRIMARY KEY,tournament_id INTEGER NOT NULL,
        home_source TEXT,away_source TEXT,bracket_id INTEGER
    )""")
    con.execute("""CREATE TABLE brackets(
        id INTEGER PRIMARY KEY,tournament_id INTEGER NOT NULL
    )""")
    con.execute("""CREATE TABLE schedule_requests(
        id INTEGER PRIMARY KEY,tournament_id INTEGER NOT NULL,team_id INTEGER,
        request_type TEXT,request_value TEXT,status TEXT
    )""")
    con.execute("""INSERT INTO groups VALUES(5,7,'Grupp A','U14',1)""")
    con.execute("""INSERT INTO teams VALUES(
        10,7,'Lag A','#111111','#eeeeee','Helfärgad','#ffffff',
        'Helfärgad','#111827',100,0,NULL,'',0,
        'Ada','070','a@example.com','U14',1,5,NULL
    )""")
    con.execute("""INSERT INTO schedule_requests VALUES(
        20,7,10,'late_start','11:00','Väntar'
    )""")
    con.commit(); con.close()


def test_stale_admin_team_edit_is_rejected(tmp_path):
    path=tmp_path/"team.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM teams WHERE id=10").fetchone(); con.close()
    snap=h["_admin_team_snapshot"](row)

    kwargs=dict(
        primary_color="#111111",secondary_color="#eeeeee",
        home_pattern="Helfärgad",home_color_2="#ffffff",
        away_pattern="Helfärgad",away_color_2="#111827",
        distance_km=100,late_first_match=False,earliest_first_time=None,
        travel_note="",avoid_late_group_match=False,
        responsible_name="Ada",responsible_phone="070",
        responsible_email="a@example.com",age_class="U14",competition_class_id=1,
    )
    assert h["_admin_update_team_if_unchanged"](10,7,snap,name="Lag Nytt",**kwargs)==(True,None)
    assert h["_admin_update_team_if_unchanged"](10,7,snap,name="Lag Gammalt",**kwargs)==(False,"conflict")

    con=sqlite3.connect(path)
    assert con.execute("SELECT name FROM teams WHERE id=10").fetchone()[0]=="Lag Nytt"
    con.close()


def test_stale_team_delete_does_not_remove_changed_team(tmp_path):
    path=tmp_path/"delete_team.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM teams WHERE id=10").fetchone()
    snap=h["_admin_team_snapshot"](row)
    con.execute("UPDATE teams SET travel_note='newer' WHERE id=10")
    con.commit(); con.close()

    assert h["_admin_delete_team_if_unchanged"](10,7,snap)==(False,"conflict")
    con=sqlite3.connect(path)
    assert con.execute("SELECT COUNT(*) FROM teams WHERE id=10").fetchone()[0]==1
    con.close()


def test_fresh_team_delete_is_tournament_scoped(tmp_path):
    path=tmp_path/"fresh_team_delete.sqlite"; _create(path)
    con=sqlite3.connect(path)
    con.execute("INSERT INTO brackets VALUES(30,7)")
    con.execute("INSERT INTO brackets VALUES(31,8)")
    con.execute("INSERT INTO matches VALUES(40,7,'team:10','team:99',30)")
    con.execute("INSERT INTO matches VALUES(41,8,'team:10','team:98',31)")
    con.commit(); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM teams WHERE id=10").fetchone(); con.close()

    h=_load(path)
    assert h["_admin_delete_team_if_unchanged"](10,7,h["_admin_team_snapshot"](row))==(True,None)

    con=sqlite3.connect(path)
    assert con.execute("SELECT COUNT(*) FROM teams WHERE id=10").fetchone()[0]==0
    assert con.execute("SELECT COUNT(*) FROM matches WHERE id=40").fetchone()[0]==0
    # Foreign tournament data with same source token remains untouched.
    assert con.execute("SELECT COUNT(*) FROM matches WHERE id=41").fetchone()[0]==1
    assert con.execute("SELECT COUNT(*) FROM brackets WHERE id=31").fetchone()[0]==1
    con.close()


def test_stale_group_edit_and_delete_are_rejected(tmp_path):
    path=tmp_path/"group.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM groups WHERE id=5").fetchone(); con.close()
    snap=h["_admin_group_snapshot"](row)

    assert h["_admin_update_group_if_unchanged"](
        5,7,snap,name="Grupp Ny",age_class="U14",competition_class_id=1
    )==(True,None)
    assert h["_admin_delete_group_if_unchanged"](5,7,snap)==(False,"conflict")


def test_schedule_request_transition_is_atomic(tmp_path):
    path=tmp_path/"request.sqlite"; _create(path)
    h=_load(path)
    transition=h["_set_schedule_request_status_if_current"]

    assert transition(20,7,"Väntar","Godkänd")== (True,None)
    assert transition(20,7,"Väntar","Nekad")== (False,"conflict")

    con=sqlite3.connect(path)
    assert con.execute("SELECT status FROM schedule_requests WHERE id=20").fetchone()[0]=="Godkänd"
    con.close()
