
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")


def test_completed_fixture_enables_playoff_when_it_seeds_bracket():
    start=E2E.index("def seed_completed_cup_fixture")
    end=E2E.index("\ndef ",start+5)
    fixture=E2E[start:end]
    assert '"A-slutspel"' in fixture
    assert "playoff_format='A- och B-slutspel'" in fixture
    assert "playoff_model_confirmed=1" in fixture
    assert '"Final"' in fixture


def test_browser_contract_still_requires_real_final_content():
    assert '("Slutspel", "playoffs", "FINAL")' in E2E


def test_completed_fixture_persists_playoff_configuration(tmp_path):
    import ast
    import sqlite3
    from datetime import datetime,timedelta

    db=tmp_path/"fixture.sqlite"
    con=sqlite3.connect(db)
    con.execute("CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER)")
    con.execute("CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER)")
    con.execute("""CREATE TABLE matches(
        id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,group_id INTEGER,
        bracket_id INTEGER,stage TEXT,round_no INTEGER,match_no INTEGER,
        home_source TEXT,away_source TEXT,home_score INTEGER,away_score INTEGER,
        decided_winner_id INTEGER,scheduled_start TEXT,pitch_number INTEGER,
        schedule_published INTEGER
    )""")
    con.execute("""CREATE TABLE brackets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,name TEXT,size INTEGER,bronze_match INTEGER
    )""")
    con.execute("""CREATE TABLE tournaments(
        id INTEGER PRIMARY KEY,is_published INTEGER,lifecycle_status TEXT,completed_at TEXT,
        playoff_format TEXT,playoff_model_confirmed INTEGER
    )""")
    con.execute("INSERT INTO tournaments VALUES(7,0,'draft',NULL,'Inget slutspel',0)")
    con.executemany("INSERT INTO groups VALUES(?,7)",[(1,),(2,)])
    con.executemany(
        "INSERT INTO teams VALUES(?,7,?)",
        [(i,1 if i<=4 else 2) for i in range(1,9)],
    )
    con.commit(); con.close()

    source=E2E
    tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="seed_completed_cup_fixture")
    module=ast.Module(body=[node],type_ignores=[])
    ast.fix_missing_locations(module)
    ns={"sqlite3":sqlite3,"DB":db,"datetime":datetime,"timedelta":timedelta}
    exec(compile(module,"e2e_fixture","exec"),ns)
    ns["seed_completed_cup_fixture"](7)

    con=sqlite3.connect(db)
    tournament=con.execute(
        "SELECT playoff_format,playoff_model_confirmed,lifecycle_status,is_published FROM tournaments WHERE id=7"
    ).fetchone()
    final_count=con.execute(
        "SELECT COUNT(*) FROM matches WHERE tournament_id=7 AND stage='Final'"
    ).fetchone()[0]
    con.close()
    assert tournament==("A- och B-slutspel",1,"completed",1)
    assert final_count==1
