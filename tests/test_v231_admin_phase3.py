
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


def _load(path):
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    names={
        "_offer_snapshot",
        "_admin_update_offer_if_unchanged",
        "_admin_delete_offer_if_unchanged",
        "_functionary_shift_snapshot",
        "_admin_delete_functionary_shift_if_unchanged",
        "_credential_snapshot",
        "_rotate_participant_code_if_unchanged",
        "_trash_tournament_if_current",
        "_restore_trashed_tournament_if_current",
        "_delete_trashed_tournament_if_current",
    }
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==names
    module=ast.Module(body=nodes,type_ignores=[])
    ast.fix_missing_locations(module)

    token_counter={"n":0}
    def generate_access_code():
        token_counter["n"] += 1
        return f"CODE{token_counter['n']}"
    def new_code_hash(code):
        return "salt",f"hash:{code}"

    ns={
        "sqlite3":sqlite3,
        "datetime":__import__("datetime").datetime,
        "db":LocalDbFactory(path),
        "_row_value":_row_value,
        "_clear_render_query_cache":lambda:None,
        "generate_access_code":generate_access_code,
        "new_code_hash":new_code_hash,
    }
    exec(compile(module,str(APP_PATH),"exec"),ns)
    return ns


def _create(path):
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE offers(
        id INTEGER PRIMARY KEY,tournament_id INTEGER,title TEXT,business_name TEXT,
        description TEXT,discount_code TEXT,valid_until TEXT,url TEXT,active INTEGER,sort_order INTEGER
    )""")
    con.execute("""CREATE TABLE functionary_shifts(
        id INTEGER PRIMARY KEY,tournament_id INTEGER,functionary_id INTEGER,
        shift_start TEXT,shift_end TEXT,assignment TEXT,location TEXT
    )""")
    con.execute("""CREATE TABLE participant_access_credentials(
        id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,team_id INTEGER,
        code_salt TEXT,code_hash TEXT,created_at TEXT,rotated_at TEXT,admin_code TEXT,
        UNIQUE(tournament_id,team_id)
    )""")
    con.execute("""CREATE TABLE tournaments(
        id INTEGER PRIMARY KEY,name TEXT,lifecycle_status TEXT,trashed_at TEXT,is_published INTEGER
    )""")
    con.execute("INSERT INTO offers VALUES(1,7,'Lunch','Café','Desc','CUP','2026-09-01','https://x.se',1,2)")
    con.execute("INSERT INTO functionary_shifts VALUES(2,7,10,'2026-09-01T08:00','2026-09-01T12:00','Kiosk','Entré')")
    con.execute("INSERT INTO tournaments VALUES(7,'Cup A','published',NULL,1)")
    con.commit(); con.close()


def test_stale_offer_update_and_delete_are_rejected(tmp_path):
    path=tmp_path/"offer.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM offers WHERE id=1").fetchone(); con.close()
    snap=h["_offer_snapshot"](row)

    assert h["_admin_update_offer_if_unchanged"](
        1,7,snap,title="Ny lunch",business_name="Café",description="Desc",
        discount_code="CUP",valid_until="2026-09-01",url="https://x.se",
        active=True,sort_order=2
    )==(True,None)

    assert h["_admin_delete_offer_if_unchanged"](1,7,snap)==(False,"conflict")


def test_stale_shift_delete_is_rejected(tmp_path):
    path=tmp_path/"shift.sqlite"; _create(path)
    h=_load(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM functionary_shifts WHERE id=2").fetchone()
    snap=h["_functionary_shift_snapshot"](row)
    con.execute("UPDATE functionary_shifts SET location='Plan 1' WHERE id=2")
    con.commit(); con.close()
    assert h["_admin_delete_functionary_shift_if_unchanged"](2,7,snap)==(False,"conflict")


def test_portal_code_rotation_is_compare_and_set(tmp_path):
    path=tmp_path/"code.sqlite"; _create(path)
    h=_load(path)

    changed,reason,code=h["_rotate_participant_code_if_unchanged"](7,10,None)
    assert changed and reason is None and code=="CODE1"

    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM participant_access_credentials WHERE tournament_id=7 AND team_id=10").fetchone()
    con.close()
    snap=h["_credential_snapshot"](row)

    changed,reason,code2=h["_rotate_participant_code_if_unchanged"](7,10,snap)
    assert changed and code2=="CODE2"

    # Old snapshot cannot overwrite the newer code.
    assert h["_rotate_participant_code_if_unchanged"](7,10,snap)[:2]==(False,"conflict")


def test_trash_restore_delete_are_state_guarded(tmp_path):
    path=tmp_path/"trash.sqlite"; _create(path)
    h=_load(path)

    assert h["_trash_tournament_if_current"](7,"published",1)==(True,None)
    assert h["_trash_tournament_if_current"](7,"published",1)==(False,"conflict")

    con=sqlite3.connect(path)
    trashed_at=con.execute("SELECT trashed_at FROM tournaments WHERE id=7").fetchone()[0]
    con.close()

    assert h["_restore_trashed_tournament_if_current"](7,trashed_at)==(True,None)
    assert h["_delete_trashed_tournament_if_current"](7,"Cup A",trashed_at)==(False,"conflict")


def test_permanent_delete_requires_same_trashed_version(tmp_path):
    path=tmp_path/"delete.sqlite"; _create(path)
    h=_load(path)
    assert h["_trash_tournament_if_current"](7,"published",1)==(True,None)
    con=sqlite3.connect(path)
    trashed_at=con.execute("SELECT trashed_at FROM tournaments WHERE id=7").fetchone()[0]
    con.close()
    assert h["_delete_trashed_tournament_if_current"](7,"Cup A",trashed_at)==(True,None)
