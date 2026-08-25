import sqlite3

from cupnavi_core.schedule_repository import ScheduleRepository


def make_db():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE tournaments(
            id INTEGER PRIMARY KEY,
            is_published INTEGER NOT NULL DEFAULT 0,
            schedule_dirty INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
        CREATE TABLE teams(
            id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,
            late_first_match INTEGER DEFAULT 0,earliest_first_time TEXT,
            avoid_late_group_match INTEGER DEFAULT 0
        );
        CREATE TABLE referees(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
        CREATE TABLE matches(
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER,
            group_id INTEGER,
            bracket_id INTEGER,
            stage TEXT,
            round_no INTEGER DEFAULT 1,
            match_no INTEGER DEFAULT 1,
            home_source TEXT,
            away_source TEXT,
            scheduled_start TEXT,
            pitch_number INTEGER,
            referee_id INTEGER,
            schedule_published INTEGER DEFAULT 0,
            schedule_locked INTEGER DEFAULT 0
        );
        """
    )
    con.execute("INSERT INTO tournaments(id,is_published,schedule_dirty) VALUES(1,1,1)")
    con.execute("INSERT INTO groups(id,tournament_id,name) VALUES(10,1,'Grupp A')")
    con.executemany(
        "INSERT INTO teams(id,tournament_id,group_id) VALUES(?,?,?)",
        [(1,1,10),(2,1,10)],
    )
    con.execute("INSERT INTO referees(id,tournament_id,name) VALUES(5,1,'Domare')")
    con.commit()
    return con


def repo_for(con, cache_marker=None):
    def fetch_all(sql, params=()):
        return con.execute(sql, params).fetchall()

    def clear():
        if cache_marker is not None:
            cache_marker.append(True)

    return ScheduleRepository(fetch_all, lambda: con, clear)


def test_group_generation_data_and_batch_insert():
    con = make_db()
    marker = []
    repo = repo_for(con, marker)

    groups, teams, existing = repo.group_generation_data(1)
    assert [row["name"] for row in groups] == ["Grupp A"]
    assert [row["id"] for row in teams] == [1, 2]
    assert existing == []

    repo.insert_group_matches([
        (1, 10, 1, "team:1", "team:2"),
    ])
    row = con.execute("SELECT * FROM matches").fetchone()
    assert row["home_source"] == "team:1"
    assert marker == [True]


def test_scheduling_inputs_are_centralized():
    con = make_db()
    repo = repo_for(con)
    repo.insert_group_matches([(1,10,1,"team:1","team:2")])

    referees, travel, matches = repo.scheduling_inputs(1)
    assert referees[0]["id"] == 5
    assert len(travel) == 2
    assert matches[0]["stage"] == "Gruppspel"


def test_persist_schedule_is_atomic_unit():
    con = make_db()
    repo = repo_for(con)
    repo.insert_group_matches([(1,10,1,"team:1","team:2")])
    match_id = con.execute("SELECT id FROM matches").fetchone()[0]

    repo.persist_generated_schedule(
        1,
        [("2026-08-21T09:00:00", 2, 5, match_id)],
        unresolved=0,
        preserve_existing=False,
    )

    match = con.execute("SELECT * FROM matches WHERE id=?", (match_id,)).fetchone()
    tournament = con.execute("SELECT * FROM tournaments WHERE id=1").fetchone()
    assert match["scheduled_start"] == "2026-08-21T09:00:00"
    assert match["pitch_number"] == 2
    assert match["referee_id"] == 5
    assert tournament["is_published"] == 0
    assert tournament["schedule_dirty"] == 0
