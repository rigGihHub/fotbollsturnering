from datetime import datetime
import sqlite3

from cupnavi_core.v137 import candidate_sort_key, normalize_schedule_strategy, travel_minutes
from cupnavi_core.migrations import apply_migrations, LATEST_SCHEMA_VERSION


def test_schedule_strategy_is_real_objective_switch():
    early_busy = (datetime(2026,8,24,9,0), 0, 0, 0, 1, None)
    later_free = (datetime(2026,8,24,9,5), 0, 0, 1, 2, None)
    loads = {1: 4, 2: 0}
    assert min([early_busy,later_free], key=lambda c: candidate_sort_key(c, 'earliest_finish', loads)) == early_busy
    assert min([early_busy,later_free], key=lambda c: candidate_sort_key(c, 'use_pitch_windows', loads)) == later_free


def test_strategy_normalization_is_safe():
    assert normalize_schedule_strategy('use_pitch_windows') == 'use_pitch_windows'
    assert normalize_schedule_strategy('nonsense') == 'earliest_finish'


def test_travel_matrix_is_symmetric_fallback_and_zero_on_same_pitch():
    matrix={(1,2):15}
    assert travel_minutes(matrix,1,2)==15
    assert travel_minutes(matrix,2,1)==15
    assert travel_minutes(matrix,1,1)==0
    assert travel_minutes(matrix,None,2)==0


def test_v137_migration_fields_and_tables_exist():
    con=sqlite3.connect(':memory:')
    con.executescript('''
    CREATE TABLE tournaments(id INTEGER PRIMARY KEY);
    CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER);
    CREATE TABLE groups(id INTEGER PRIMARY KEY, tournament_id INTEGER);
    CREATE TABLE players(id INTEGER PRIMARY KEY, team_id INTEGER);
    CREATE TABLE referees(id INTEGER PRIMARY KEY, tournament_id INTEGER);
    CREATE TABLE matches(id INTEGER PRIMARY KEY, tournament_id INTEGER, group_id INTEGER, bracket_id INTEGER, scheduled_start TEXT);
    CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY, match_id INTEGER);
    CREATE TABLE feedback(id INTEGER PRIMARY KEY, tournament_id INTEGER);
    CREATE TABLE offers(id INTEGER PRIMARY KEY, tournament_id INTEGER, active INTEGER, sort_order INTEGER);
    CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY);
    CREATE TABLE team_messages(id INTEGER PRIMARY KEY, tournament_id INTEGER, sender_type TEXT, sender_team_id INTEGER, recipient_type TEXT, recipient_team_id INTEGER, created_at TEXT, subject TEXT, message TEXT, read_at TEXT);
    CREATE TABLE pitches(tournament_id INTEGER, pitch_number INTEGER, name TEXT, PRIMARY KEY(tournament_id,pitch_number));
    ''')
    # Mark v18 because this unit test targets only the newly released migration.
    con.execute('CREATE TABLE cupnavi_schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)')
    con.execute("INSERT INTO cupnavi_schema_migrations VALUES(18,'named_pitches_v134','now')")
    applied=apply_migrations(con)
    assert applied == [19, 20, 21, 22, 23, 24]
    assert LATEST_SCHEMA_VERSION == 24
    schedule_cols={r[1] for r in con.execute('PRAGMA table_info(schedule_rules)')}
    pitch_cols={r[1] for r in con.execute('PRAGMA table_info(pitches)')}
    message_cols={r[1] for r in con.execute('PRAGMA table_info(team_messages)')}
    assert {'schedule_strategy','consider_pitch_travel'} <= schedule_cols
    assert 'address' in pitch_cols
    assert {'email_status','email_error'} <= message_cols
    assert con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pitch_travel_times'").fetchone()
