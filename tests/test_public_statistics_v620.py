import sqlite3

from cupnavi_api import repository


def test_public_statistics_aggregates_registered_player_events(tmp_path, monkeypatch):
    db_path = tmp_path / "cupnavi-v620.db"
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER, name TEXT);
        CREATE TABLE players(id INTEGER PRIMARY KEY, team_id INTEGER, name TEXT, player_number INTEGER);
        CREATE TABLE matches(id INTEGER PRIMARY KEY, tournament_id INTEGER);
        CREATE TABLE player_match_stats(
            match_id INTEGER,
            player_id INTEGER,
            goals INTEGER,
            assists INTEGER,
            yellow_cards INTEGER,
            red_cards INTEGER
        );
        """
    )
    con.executemany("INSERT INTO teams VALUES(?,?,?)", [(1, 34, "ÖSK"), (2, 34, "Karlslund")])
    con.executemany(
        "INSERT INTO players VALUES(?,?,?,?)",
        [(10, 1, "Alex", 9), (11, 1, "Sam", 7), (20, 2, "Kim", 10)],
    )
    con.executemany("INSERT INTO matches VALUES(?,?)", [(100, 34), (101, 34), (200, 99)])
    con.executemany(
        "INSERT INTO player_match_stats VALUES(?,?,?,?,?,?)",
        [
            (100, 10, 2, 0, 1, 0),
            (101, 10, 1, 1, 0, 0),
            (100, 11, 0, 2, 0, 0),
            (100, 20, 1, 0, 0, 1),
            (200, 10, 99, 99, 99, 99),
        ],
    )
    con.commit()
    con.close()

    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(db_path))

    payload = repository.public_statistics(34)

    assert [(row["player_name"], row["goals"]) for row in payload["scorers"]] == [
        ("Alex", 3),
        ("Kim", 1),
    ]
    assert [(row["player_name"], row["assists"]) for row in payload["assists"]] == [
        ("Sam", 2),
        ("Alex", 1),
    ]
    assert payload["cards"][0]["player_name"] == "Kim"
    assert payload["cards"][0]["red_cards"] == 1
    assert [row["team_name"] for row in payload["discipline"]] == ["ÖSK", "Karlslund"]


def test_public_statistics_does_not_invent_unregistered_goals(tmp_path, monkeypatch):
    db_path = tmp_path / "cupnavi-v620-empty.db"
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER, name TEXT);
        CREATE TABLE players(id INTEGER PRIMARY KEY, team_id INTEGER, name TEXT, player_number INTEGER);
        CREATE TABLE matches(id INTEGER PRIMARY KEY, tournament_id INTEGER);
        CREATE TABLE player_match_stats(match_id INTEGER, player_id INTEGER, goals INTEGER, assists INTEGER, yellow_cards INTEGER, red_cards INTEGER);
        INSERT INTO teams VALUES(1,34,'ÖSK');
        INSERT INTO players VALUES(10,1,'Alex',9);
        INSERT INTO matches VALUES(100,34);
        """
    )
    con.commit()
    con.close()

    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(db_path))

    payload = repository.public_statistics(34)
    assert payload == {"scorers": [], "assists": [], "cards": [], "discipline": []}
