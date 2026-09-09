
import ast
import sqlite3
from pathlib import Path

from cupnavi_core.match_reporter_logic import result_snapshot

ROOT=Path(__file__).resolve().parents[1]
APP_PATH=ROOT/"app.py"


def _load_update_function():
    """Load the actual app implementation without importing/running Streamlit."""
    source=APP_PATH.read_text(encoding="utf-8")
    tree=ast.parse(source)
    node=next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef)
        and item.name=="update_match_result_if_unchanged"
    )
    module=ast.Module(body=[node],type_ignores=[])
    ast.fix_missing_locations(module)
    namespace={"sqlite3":sqlite3}
    exec(compile(module,str(APP_PATH),"exec"),namespace)
    return namespace["update_match_result_if_unchanged"]


def _create_db(path):
    con=sqlite3.connect(path)
    con.row_factory=sqlite3.Row
    con.execute("""
        CREATE TABLE matches(
            id INTEGER PRIMARY KEY,
            home_score INTEGER,
            away_score INTEGER,
            home_penalties INTEGER,
            away_penalties INTEGER,
            decided_winner_id INTEGER,
            referee_id INTEGER
        )
    """)
    con.execute(
        "INSERT INTO matches(id,home_score,away_score,home_penalties,away_penalties,decided_winner_id,referee_id) "
        "VALUES(1,NULL,NULL,NULL,NULL,NULL,7)"
    )
    con.commit()
    con.close()


def test_two_reporters_stale_snapshot_cannot_overwrite_first_save(tmp_path):
    db_path=tmp_path/"concurrency.sqlite"
    _create_db(db_path)
    update=_load_update_function()

    # Two independent sessions read the same original state.
    con_a=sqlite3.connect(db_path)
    con_a.row_factory=sqlite3.Row
    con_b=sqlite3.connect(db_path)
    con_b.row_factory=sqlite3.Row

    original_a=result_snapshot(con_a.execute("SELECT * FROM matches WHERE id=1").fetchone())
    original_b=result_snapshot(con_b.execute("SELECT * FROM matches WHERE id=1").fetchone())
    assert original_a==original_b

    # Reporter A wins the race.
    assert update(
        con_a,1,original_a,
        home_score=2,away_score=1,
        home_penalties=None,away_penalties=None,
        decided_winner_id=None,referee_id=7,
    ) is True
    con_a.commit()

    # Reporter B uses the now-stale snapshot and must not overwrite A.
    assert update(
        con_b,1,original_b,
        home_score=0,away_score=3,
        home_penalties=None,away_penalties=None,
        decided_winner_id=None,referee_id=7,
    ) is False
    con_b.commit()

    final=con_b.execute(
        "SELECT home_score,away_score,referee_id FROM matches WHERE id=1"
    ).fetchone()
    assert tuple(final)==(2,1,7)

    con_a.close()
    con_b.close()


def test_referee_change_also_invalidates_stale_snapshot(tmp_path):
    db_path=tmp_path/"referee.sqlite"
    _create_db(db_path)
    update=_load_update_function()

    con1=sqlite3.connect(db_path)
    con1.row_factory=sqlite3.Row
    con2=sqlite3.connect(db_path)
    con2.row_factory=sqlite3.Row

    stale=result_snapshot(con2.execute("SELECT * FROM matches WHERE id=1").fetchone())

    con1.execute("UPDATE matches SET referee_id=9 WHERE id=1")
    con1.commit()

    assert update(
        con2,1,stale,
        home_score=1,away_score=0,
        referee_id=7,
    ) is False

    row=con2.execute("SELECT home_score,away_score,referee_id FROM matches WHERE id=1").fetchone()
    assert tuple(row)==(None,None,9)

    con1.close()
    con2.close()


def test_result_snapshot_supports_sqlite_row(tmp_path):
    db_path=tmp_path/"snapshot.sqlite"
    _create_db(db_path)
    con=sqlite3.connect(db_path)
    con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM matches WHERE id=1").fetchone()
    assert result_snapshot(row)=={
        "home_score":None,
        "away_score":None,
        "home_penalties":None,
        "away_penalties":None,
        "decided_winner_id":None,
        "referee_id":7,
    }
    con.close()
