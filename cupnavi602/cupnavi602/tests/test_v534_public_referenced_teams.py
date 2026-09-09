from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text()
WORKSPACE = (ROOT / 'cupnavi_core' / 'public_workspace_view.py').read_text()
MATCHES = (ROOT / 'cupnavi_core' / 'public_matches_view.py').read_text()
VERSION = (ROOT / 'VERSION.txt').read_text().strip()


def _future_sql():
    marker = 'team_stats AS (SELECT COUNT(*) AS team_total FROM teams WHERE tournament_id=?)'
    pos = APP.index(marker)
    start = APP.rfind('_combined_sql = f"""', 0, pos) + len('_combined_sql = f"""')
    end = APP.index('"""', pos)
    sql = APP[start:end]
    return sql.replace('{_match_limit_sql}', ' LIMIT ?')


def test_version_and_contract_wiring():
    assert VERSION == '2026.09.08-534-PUBLIC-REFERENCED-TEAMS'
    assert 'public_team_total=_published_team_total' in WORKSPACE
    assert 'team_count = len(public_teams) if public_team_total is None else int(public_team_total or 0)' in MATCHES
    assert '_cupnavi_public_core_v534_' in APP


def test_future_first_batch_transfers_only_referenced_teams_but_keeps_exact_total():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('''
        CREATE TABLE matches (
            id INTEGER PRIMARY KEY, tournament_id INTEGER, group_id INTEGER, bracket_id INTEGER,
            stage TEXT, round_no INTEGER, match_no INTEGER, home_source TEXT, away_source TEXT,
            home_score INTEGER, away_score INTEGER, home_penalties INTEGER, away_penalties INTEGER,
            referee_id INTEGER, schedule_published INTEGER, decided_winner_id INTEGER,
            scheduled_start TEXT, pitch_number INTEGER
        );
        CREATE TABLE teams (
            id INTEGER PRIMARY KEY, tournament_id INTEGER, group_id INTEGER, name TEXT, age_class TEXT,
            primary_color TEXT, secondary_color TEXT, home_pattern TEXT, home_color_2 TEXT,
            away_pattern TEXT, away_color_2 TEXT
        );
        CREATE TABLE referees (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE pitches (tournament_id INTEGER, pitch_number INTEGER, name TEXT);
    ''')
    for team_id in range(1, 41):
        con.execute('INSERT INTO teams VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (team_id, 1, 1, f'Team {team_id}', 'P14', '#111', '#222', '', '', '', ''))
    # First 12 matches only reference teams 1..24. Later matches reference 25..40.
    for match_id in range(1, 21):
        home = ((match_id - 1) * 2) % 40 + 1
        away = (home % 40) + 1
        con.execute('INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (match_id, 1, 1, None, 'Grupp', 1, match_id,
                     f'team:{home}', f'team:{away}', None, None, None, None,
                     None, 1, None, f'2026-09-20T{8 + match_id//6:02d}:{(match_id%6)*10:02d}:00', 1))
    rows = list(con.execute(_future_sql(), (1, 12, 1, 1)))
    match_rows = [r for r in rows if r['row_kind'] == 'match']
    team_rows = [r for r in rows if r['row_kind'] == 'team']
    assert len(match_rows) == 12
    assert {r['id'] for r in team_rows} == set(range(1, 25))
    assert max(int(r['team_total']) for r in rows) == 40
    assert max(int(r['match_total']) for r in match_rows) == 20


def test_full_team_query_remains_available_outside_server_batch():
    assert 'FROM teams WHERE tournament_id=? ORDER BY name' in APP
