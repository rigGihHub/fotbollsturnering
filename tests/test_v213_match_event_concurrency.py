
import ast
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP_PATH=ROOT/"app.py"


def _load_update_function():
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    node=next(
        item for item in tree.body
        if isinstance(item,ast.FunctionDef)
        and item.name=="update_player_match_stats_if_unchanged"
    )
    module=ast.Module(body=[node],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace={"sqlite3":sqlite3}
    exec(compile(module,str(APP_PATH),"exec"),namespace)
    return namespace["update_player_match_stats_if_unchanged"]


def _create_db(path, *, existing=False):
    con=sqlite3.connect(path)
    con.row_factory=sqlite3.Row
    con.execute("""
        CREATE TABLE player_match_stats(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            goals INTEGER NOT NULL DEFAULT 0,
            assists INTEGER NOT NULL DEFAULT 0,
            yellow_cards INTEGER NOT NULL DEFAULT 0,
            red_cards INTEGER NOT NULL DEFAULT 0,
            UNIQUE(match_id,player_id)
        )
    """)
    if existing:
        con.execute(
            "INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards) "
            "VALUES(1,10,0,0,0,0)"
        )
    con.commit()
    con.close()


def _snapshot_zero():
    return {"goals":0,"assists":0,"yellow_cards":0,"red_cards":0}


def test_two_reporters_cannot_overwrite_same_existing_player_stats(tmp_path):
    db_path=tmp_path/"existing.sqlite"
    _create_db(db_path,existing=True)
    update=_load_update_function()

    con_a=sqlite3.connect(db_path)
    con_a.row_factory=sqlite3.Row
    con_b=sqlite3.connect(db_path)
    con_b.row_factory=sqlite3.Row

    expected_a=_snapshot_zero()
    expected_b=_snapshot_zero()

    assert update(
        con_a,1,10,expected_a,
        goals=1,assists=1,yellow_cards=0,red_cards=0,
    ) is True
    con_a.commit()

    assert update(
        con_b,1,10,expected_b,
        goals=2,assists=0,yellow_cards=1,red_cards=0,
    ) is False
    con_b.commit()

    final=con_b.execute(
        "SELECT goals,assists,yellow_cards,red_cards FROM player_match_stats "
        "WHERE match_id=1 AND player_id=10"
    ).fetchone()
    assert tuple(final)==(1,1,0,0)

    con_a.close()
    con_b.close()


def test_two_reporters_cannot_overwrite_concurrent_first_insert(tmp_path):
    db_path=tmp_path/"newrow.sqlite"
    _create_db(db_path,existing=False)
    update=_load_update_function()

    con_a=sqlite3.connect(db_path)
    con_b=sqlite3.connect(db_path)

    assert update(
        con_a,1,10,_snapshot_zero(),
        goals=1,assists=0,yellow_cards=0,red_cards=0,
    ) is True
    con_a.commit()

    # B's editor was also loaded when no row existed (zero snapshot).
    # The now-existing non-zero row must not be overwritten.
    assert update(
        con_b,1,10,_snapshot_zero(),
        goals=0,assists=1,yellow_cards=0,red_cards=0,
    ) is False
    con_b.commit()

    final=con_b.execute(
        "SELECT goals,assists,yellow_cards,red_cards FROM player_match_stats "
        "WHERE match_id=1 AND player_id=10"
    ).fetchone()
    assert tuple(final)==(1,0,0,0)

    con_a.close()
    con_b.close()


def test_fresh_snapshot_can_update_existing_event_row(tmp_path):
    db_path=tmp_path/"fresh.sqlite"
    _create_db(db_path,existing=True)
    update=_load_update_function()
    con=sqlite3.connect(db_path)

    assert update(
        con,1,10,_snapshot_zero(),
        goals=1,assists=0,yellow_cards=1,red_cards=0,
    ) is True
    con.commit()

    assert update(
        con,1,10,
        {"goals":1,"assists":0,"yellow_cards":1,"red_cards":0},
        goals=1,assists=1,yellow_cards=1,red_cards=0,
    ) is True
    con.commit()

    final=con.execute(
        "SELECT goals,assists,yellow_cards,red_cards FROM player_match_stats "
        "WHERE match_id=1 AND player_id=10"
    ).fetchone()
    assert tuple(final)==(1,1,1,0)
    con.close()
