
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
    names={"_team_contact_snapshot","_save_team_contact_if_unchanged","_mark_team_messages_read"}
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
        "datetime":__import__("datetime").datetime,
    }
    exec(compile(module,str(APP_PATH),"exec"),ns)
    return ns


def _create(path):
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE teams(
        id INTEGER PRIMARY KEY,
        responsible_name TEXT,responsible_phone TEXT,responsible_email TEXT,
        public_contact_name TEXT,public_contact_phone TEXT,public_contact_email TEXT,
        public_contact_enabled INTEGER DEFAULT 0
    )""")
    con.execute("""CREATE TABLE team_messages(
        id INTEGER PRIMARY KEY,tournament_id INTEGER,sender_type TEXT,sender_team_id INTEGER,
        recipient_type TEXT,recipient_team_id INTEGER,created_at TEXT,subject TEXT,message TEXT,read_at TEXT
    )""")
    con.execute("""INSERT INTO teams VALUES(
        10,'Old Name','070','old@example.com','Old Name','070','old@example.com',1
    )""")
    con.executemany(
        "INSERT INTO team_messages VALUES(?,?,?,?,?,?,?,?,?,NULL)",
        [
            (1,7,'organizer',None,'team',10,'t','A','x'),
            (2,7,'organizer',None,'team',11,'t','B','x'),
            (3,7,'team',10,'organizer',None,'t','C','x'),
            (4,8,'organizer',None,'team',10,'t','D','x'),
        ],
    )
    con.commit(); con.close()


def test_stale_contact_edit_cannot_overwrite_newer_contact(tmp_path):
    path=tmp_path/"contact.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    original=con.execute("SELECT * FROM teams WHERE id=10").fetchone()
    con.close()
    snap=h["_team_contact_snapshot"](original)

    assert h["_save_team_contact_if_unchanged"](
        10,snap,contact_name="New",contact_phone="071",contact_email="new@example.com",public_enabled=1
    )==(True,None)

    assert h["_save_team_contact_if_unchanged"](
        10,snap,contact_name="Stale",contact_phone="072",contact_email="stale@example.com",public_enabled=0
    )==(False,"conflict")


def test_invalid_contact_email_is_rejected(tmp_path):
    path=tmp_path/"email.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    snap=h["_team_contact_snapshot"](con.execute("SELECT * FROM teams WHERE id=10").fetchone())
    con.close()
    assert h["_save_team_contact_if_unchanged"](
        10,snap,contact_name="X",contact_phone="",contact_email="not-an-email",public_enabled=0
    )==(False,"invalid_email")


def test_mark_read_cannot_touch_other_team_or_tournament(tmp_path):
    path=tmp_path/"messages.sqlite"; _create(path)
    h=_load(path)
    changed=h["_mark_team_messages_read"](
        [1,2,4],tournament_id=7,recipient_type="team",recipient_team_id=10
    )
    assert changed==1

    con=sqlite3.connect(path)
    rows=dict(con.execute("SELECT id,read_at FROM team_messages").fetchall())
    con.close()
    assert rows[1] is not None
    assert rows[2] is None
    assert rows[4] is None


def test_organizer_mark_read_only_touches_organizer_inbox(tmp_path):
    path=tmp_path/"organizer.sqlite"; _create(path)
    h=_load(path)
    assert h["_mark_team_messages_read"](
        [1,3],tournament_id=7,recipient_type="organizer"
    )==1
    con=sqlite3.connect(path)
    rows=dict(con.execute("SELECT id,read_at FROM team_messages").fetchall())
    con.close()
    assert rows[3] is not None
    assert rows[1] is None
