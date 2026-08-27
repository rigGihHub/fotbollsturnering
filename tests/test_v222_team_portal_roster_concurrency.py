
import ast
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP_PATH=ROOT/"app.py"


class LocalDbFactory:
    def __init__(self,path):
        self.path=path
    def __call__(self):
        con=sqlite3.connect(self.path,timeout=5)
        con.row_factory=sqlite3.Row
        return con


def _load_save(db_factory):
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    node=next(
        item for item in tree.body
        if isinstance(item,ast.FunctionDef)
        and item.name=="_save_match_roster_if_unchanged"
    )
    module=ast.Module(body=[node],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace={
        "datetime":__import__("datetime").datetime,
        "sqlite3":sqlite3,
        "db":db_factory,
        "CLOUD_DATABASE_ENABLED":False,
        "_clear_render_query_cache":lambda:None,
    }
    exec(compile(module,str(APP_PATH),"exec"),namespace)
    return namespace["_save_match_roster_if_unchanged"]


def _db(path):
    con=sqlite3.connect(path)
    con.execute("CREATE TABLE players(id INTEGER PRIMARY KEY,team_id INTEGER NOT NULL)")
    con.execute("""CREATE TABLE match_rosters(
        match_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        selected_at TEXT,
        selected_by TEXT,
        UNIQUE(match_id,team_id,player_id)
    )""")
    con.executemany("INSERT INTO players(id,team_id) VALUES(?,?)",[(1,10),(2,10),(3,10),(99,11)])
    con.executemany(
        "INSERT INTO match_rosters(match_id,team_id,player_id,selected_at,selected_by) VALUES(1,10,?,?,?)",
        [(1,"old","A"),(2,"old","A")],
    )
    con.commit()
    con.close()


def test_stale_roster_snapshot_cannot_overwrite_newer_save(tmp_path):
    path=tmp_path/"roster.sqlite"
    _db(path)
    save=_load_save(LocalDbFactory(path))

    ok,reason=save(1,10,[1,3],[1,2],"Leader A")
    assert (ok,reason)==(True,None)

    ok,reason=save(1,10,[2],[1,2],"Leader B")
    assert (ok,reason)==(False,"conflict")

    con=sqlite3.connect(path)
    ids=[r[0] for r in con.execute(
        "SELECT player_id FROM match_rosters WHERE match_id=1 AND team_id=10 ORDER BY player_id"
    )]
    con.close()
    assert ids==[1,3]


def test_roster_rejects_player_from_other_team(tmp_path):
    path=tmp_path/"ownership.sqlite"
    _db(path)
    save=_load_save(LocalDbFactory(path))

    ok,reason=save(1,10,[1,99],[1,2],"Leader")
    assert (ok,reason)==(False,"invalid_players")

    con=sqlite3.connect(path)
    ids=[r[0] for r in con.execute(
        "SELECT player_id FROM match_rosters WHERE match_id=1 AND team_id=10 ORDER BY player_id"
    )]
    con.close()
    assert ids==[1,2]


def test_fresh_snapshot_can_replace_roster_atomically(tmp_path):
    path=tmp_path/"fresh.sqlite"
    _db(path)
    save=_load_save(LocalDbFactory(path))

    assert save(1,10,[2,3],[1,2],"Leader")== (True,None)
    con=sqlite3.connect(path)
    ids=[r[0] for r in con.execute(
        "SELECT player_id FROM match_rosters WHERE match_id=1 AND team_id=10 ORDER BY player_id"
    )]
    con.close()
    assert ids==[2,3]
