
import ast
import json
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


def _load(path):
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    names={
        "_sponsor_snapshot",
        "_admin_update_sponsor_if_unchanged",
        "_admin_delete_sponsor_if_unchanged",
        "_functionary_snapshot",
        "_admin_update_functionary_if_unchanged",
        "_admin_delete_functionary_if_unchanged",
        "_set_publication_if_current",
        "_set_lifecycle_if_current",
        "_undo_audit_entry_if_current",
    }
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==names
    module=ast.Module(body=nodes,type_ignores=[])
    ast.fix_missing_locations(module)
    ns={
        "sqlite3":sqlite3,
        "json":json,
        "datetime":__import__("datetime").datetime,
        "db":LocalDbFactory(path),
        "_row_value":_row_value,
        "_clear_render_query_cache":lambda:None,
    }
    exec(compile(module,str(APP_PATH),"exec"),ns)
    return ns


def _create(path):
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE sponsors(
        id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,level TEXT,
        description TEXT,website_url TEXT,logo_data_uri TEXT,active INTEGER,sort_order INTEGER
    )""")
    con.execute("""CREATE TABLE functionaries(
        id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,role TEXT,phone TEXT,email TEXT,
        pitch_number INTEGER,notes TEXT,public_contact INTEGER,active INTEGER
    )""")
    con.execute("""CREATE TABLE tournaments(
        id INTEGER PRIMARY KEY,is_published INTEGER,published_once INTEGER,
        lifecycle_status TEXT,completed_at TEXT
    )""")
    con.execute("""CREATE TABLE matches(
        id INTEGER PRIMARY KEY,tournament_id INTEGER,scheduled_start TEXT,pitch_number INTEGER,
        schedule_published INTEGER
    )""")
    con.execute("""CREATE TABLE audit_log(
        id INTEGER PRIMARY KEY,tournament_id INTEGER,created_at TEXT,action_type TEXT,
        entity_type TEXT,entity_id INTEGER,description TEXT,before_json TEXT,after_json TEXT,
        actor TEXT,reversible INTEGER,undone_at TEXT
    )""")
    con.execute("INSERT INTO sponsors VALUES(1,7,'Sponsor A','Partner','Desc','https://a.se',NULL,1,1)")
    con.execute("INSERT INTO functionaries VALUES(2,7,'Fia','Kiosk','070','fia@example.com',1,'Not',0,1)")
    con.execute("INSERT INTO tournaments VALUES(7,0,0,'draft',NULL)")
    con.execute("INSERT INTO tournaments VALUES(8,0,0,'draft',NULL)")
    con.execute("INSERT INTO matches VALUES(10,7,'2026-09-01T10:00',1,0)")
    con.execute("INSERT INTO matches VALUES(11,8,'2026-09-01T11:00',2,0)")
    before=json.dumps({"scheduled_start":"2026-09-01T09:00","pitch_number":3})
    con.execute(
        "INSERT INTO audit_log VALUES(20,7,'t','schedule_move','match',10,'Flyttade match',?,NULL,'Admin',1,NULL)",
        (before,),
    )
    con.commit(); con.close()


def test_stale_sponsor_edit_and_delete_are_rejected(tmp_path):
    path=tmp_path/"sponsor.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM sponsors WHERE id=1").fetchone(); con.close()
    snap=h["_sponsor_snapshot"](row)

    assert h["_admin_update_sponsor_if_unchanged"](
        1,7,snap,name="Sponsor Ny",level="Partner",description="Desc",
        website_url="https://a.se",logo_data_uri=None,active=True,sort_order=1
    )==(True,None)

    assert h["_admin_delete_sponsor_if_unchanged"](1,7,snap)==(False,"conflict")


def test_functionary_stale_edit_is_rejected_and_email_validated(tmp_path):
    path=tmp_path/"fn.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM functionaries WHERE id=2").fetchone(); con.close()
    snap=h["_functionary_snapshot"](row)

    assert h["_admin_update_functionary_if_unchanged"](
        2,7,snap,name="Fia",role="Kiosk",phone="071",email="bad",
        pitch_number=1,notes="Not",public_contact=False
    )==(False,"invalid_email")

    assert h["_admin_update_functionary_if_unchanged"](
        2,7,snap,name="Fia Ny",role="Kiosk",phone="071",email="fia@example.com",
        pitch_number=1,notes="Not",public_contact=False
    )==(True,None)

    assert h["_admin_update_functionary_if_unchanged"](
        2,7,snap,name="Fia Gammal",role="Kiosk",phone="072",email="fia@example.com",
        pitch_number=1,notes="Not",public_contact=False
    )==(False,"conflict")


def test_stale_publish_rolls_back_match_publication(tmp_path):
    path=tmp_path/"publish.sqlite"; _create(path)
    h=_load(path)

    # Another Admin changed lifecycle after this browser rendered draft.
    con=sqlite3.connect(path)
    con.execute("UPDATE tournaments SET lifecycle_status='live',is_published=1 WHERE id=7")
    con.commit(); con.close()

    assert h["_set_publication_if_current"](
        7,expected_is_published=0,expected_lifecycle="draft",publish=True
    )==(False,"conflict")

    con=sqlite3.connect(path)
    assert con.execute("SELECT schedule_published FROM matches WHERE id=10").fetchone()[0]==0
    con.close()


def test_lifecycle_transition_is_compare_and_set(tmp_path):
    path=tmp_path/"life.sqlite"; _create(path)
    h=_load(path)

    con=sqlite3.connect(path)
    con.execute("UPDATE tournaments SET lifecycle_status='published',is_published=1 WHERE id=7")
    con.commit(); con.close()

    assert h["_set_lifecycle_if_current"](7,"published","live",expected_is_published=1)==(True,None)
    assert h["_set_lifecycle_if_current"](7,"published","completed",expected_is_published=1)==(False,"conflict")


def test_audit_undo_is_atomic_and_single_use(tmp_path):
    path=tmp_path/"undo.sqlite"; _create(path)
    h=_load(path)

    assert h["_undo_audit_entry_if_current"](20,7)[0] is True
    assert h["_undo_audit_entry_if_current"](20,7)[:2]==(False,"conflict")

    con=sqlite3.connect(path)
    row=con.execute("SELECT scheduled_start,pitch_number FROM matches WHERE id=10").fetchone()
    undone=con.execute("SELECT undone_at FROM audit_log WHERE id=20").fetchone()[0]
    foreign=con.execute("SELECT scheduled_start,pitch_number FROM matches WHERE id=11").fetchone()
    con.close()
    assert row==("2026-09-01T09:00",3)
    assert undone is not None
    assert foreign==("2026-09-01T11:00",2)
