
import ast
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP_PATH=ROOT/"app.py"


class LocalDbFactory:
    def __init__(self,path): self.path=path
    def __call__(self):
        con=sqlite3.connect(self.path,timeout=5)
        con.row_factory=sqlite3.Row
        return con


def _row_value(row,key,default=None):
    try: value=row[key]
    except (KeyError,IndexError,TypeError):
        try: value=row.get(key,default)
        except AttributeError: value=default
    return default if value is None and default is not None else value


def _load(path):
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    names={"_player_snapshot","_add_team_player_if_capacity","_update_team_player_if_unchanged","_delete_team_player_if_unchanged"}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==names
    module=ast.Module(body=nodes,type_ignores=[])
    ast.fix_missing_locations(module)
    ns={"sqlite3":sqlite3,"db":LocalDbFactory(path),"_row_value":_row_value,"_clear_render_query_cache":lambda:None}
    exec(compile(module,str(APP_PATH),"exec"),ns)
    return ns


def _create(path):
    con=sqlite3.connect(path)
    con.execute("""CREATE TABLE players(
        id INTEGER PRIMARY KEY AUTOINCREMENT,team_id INTEGER NOT NULL,
        player_number INTEGER,name TEXT NOT NULL,first_name TEXT,last_name TEXT,
        birth_year INTEGER,position TEXT,is_protected INTEGER NOT NULL DEFAULT 0
    )""")
    con.commit(); con.close()


def _seed(path):
    con=sqlite3.connect(path)
    con.execute("""INSERT INTO players(team_id,player_number,name,first_name,last_name,birth_year,position,is_protected)
                   VALUES(10,7,'Ada Lund','Ada','Lund',2012,'Mittfältare',0)""")
    con.commit(); con.close()


def test_atomic_capacity_blocks_stale_second_add(tmp_path):
    path=tmp_path/"capacity.sqlite"; _create(path); _seed(path)
    h=_load(path); add=h["_add_team_player_if_capacity"]
    assert add(10,2,player_number=8,name="Bo Ek",first_name="Bo",last_name="Ek",birth_year=2012,position="",is_protected=False)==(True,None)
    assert add(10,2,player_number=9,name="Cia Ny",first_name="Cia",last_name="Ny",birth_year=2012,position="",is_protected=False)==(False,"roster_full")
    con=sqlite3.connect(path)
    assert con.execute("SELECT COUNT(*) FROM players WHERE team_id=10").fetchone()[0]==2
    con.close()


def test_stale_edit_cannot_overwrite_newer_edit(tmp_path):
    path=tmp_path/"edit.sqlite"; _create(path); _seed(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    original=con.execute("SELECT * FROM players WHERE id=1").fetchone(); con.close()
    h=_load(path); snap=h["_player_snapshot"](original); update=h["_update_team_player_if_unchanged"]
    assert update(1,10,snap,player_number=7,name="Ada Nya",first_name="Ada",last_name="Nya",birth_year=2012,position="Anfallare",is_protected=False)==(True,None)
    assert update(1,10,snap,player_number=10,name="Ada Gammal",first_name="Ada",last_name="Gammal",birth_year=2011,position="Back",is_protected=False)==(False,"conflict")
    con=sqlite3.connect(path)
    assert con.execute("SELECT name,player_number,birth_year,position FROM players WHERE id=1").fetchone()==("Ada Nya",7,2012,"Anfallare")
    con.close()


def test_stale_delete_does_not_remove_newer_version(tmp_path):
    path=tmp_path/"delete.sqlite"; _create(path); _seed(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    original=con.execute("SELECT * FROM players WHERE id=1").fetchone(); con.close()
    h=_load(path); snap=h["_player_snapshot"](original)
    assert h["_update_team_player_if_unchanged"](1,10,snap,player_number=7,name="Ada Uppdaterad",first_name="Ada",last_name="Uppdaterad",birth_year=2012,position="Back",is_protected=True)==(True,None)
    assert h["_delete_team_player_if_unchanged"](1,10,snap)==(False,"conflict")
    con=sqlite3.connect(path)
    assert con.execute("SELECT name,is_protected FROM players WHERE id=1").fetchone()==("Ada Uppdaterad",1)
    con.close()


def test_fresh_delete_succeeds(tmp_path):
    path=tmp_path/"fresh.sqlite"; _create(path); _seed(path)
    con=sqlite3.connect(path); con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM players WHERE id=1").fetchone(); con.close()
    h=_load(path)
    assert h["_delete_team_player_if_unchanged"](1,10,h["_player_snapshot"](row))==(True,None)
