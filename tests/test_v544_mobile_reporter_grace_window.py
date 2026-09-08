from pathlib import Path
import json
import sqlite3

from cupnavi_core.push_notification_service import enqueue_goal_push_events, cancel_pending_goal_push_events

ROOT = Path(__file__).resolve().parents[1]


def test_v544_reporter_mobile_contract():
    text = (ROOT / 'cupnavi_core' / 'match_reporter_workspace_view.py').read_text()
    assert 'REPORTER_CORRECTION_WINDOW_SECONDS = 15' in text
    assert 'min-height: 64px' in text
    assert 'Snabbrapportera mål' in text
    assert 'reporter_inline_scorer_' in text
    assert 'inline_goal_minus_' in text and 'inline_goal_plus_' in text
    assert 'fetch_match_team_players' in text
    assert '_render_reporter_correction_window(int(quick_match_id))' in text


def test_v544_goal_push_waits_and_supersedes_latest_edit():
    con = sqlite3.connect(':memory:')
    con.execute('''CREATE TABLE push_notification_outbox(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL, team_id INTEGER NOT NULL, match_id INTEGER,
        event_type TEXT NOT NULL, event_key TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL, body TEXT NOT NULL, payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
        attempted_at TEXT, delivered_at TEXT, error TEXT
    )''')
    base = dict(
        match_id=10, tournament_id=20, home_team_id=1, away_team_id=2,
        home_team_name='Hemma', away_team_name='Borta', old_away_score=0, new_away_score=0,
    )
    assert enqueue_goal_push_events(con, old_home_score=0, new_home_score=1, **base) == 1
    first = con.execute("SELECT status,payload_json FROM push_notification_outbox").fetchone()
    payload = json.loads(first[1])
    assert first[0] == 'pending'
    assert payload['debounce_seconds'] == 30
    assert payload['deliver_after']
    assert payload['debounce_key'] == 'goal:10:home'

    assert enqueue_goal_push_events(con, old_home_score=1, new_home_score=2, **base) == 1
    rows = con.execute("SELECT status FROM push_notification_outbox ORDER BY id").fetchall()
    assert rows == [('superseded',), ('pending',)]
    assert cancel_pending_goal_push_events(con, match_id=10, team_id=1) == 1
    assert con.execute("SELECT COUNT(*) FROM push_notification_outbox WHERE status='pending'").fetchone()[0] == 0


def test_v544_version_synced():
    expected = '2026.09.08-544-MOBILE-REPORTER-GRACE-WINDOW'
    assert (ROOT / 'VERSION.txt').read_text().strip() == expected
    assert expected in (ROOT / 'cupnavi_core' / 'version.py').read_text()
    assert expected in (ROOT / 'app.py').read_text()
