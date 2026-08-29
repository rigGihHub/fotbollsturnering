from datetime import datetime, timedelta

from cupnavi_core.public_team_follow import (
    build_favorite_team_hero_html,
    build_favorite_team_snapshot,
)


def row_value(row, key, default=None):
    return row.get(key, default)


def source_team_id(source):
    try:
        return int(str(source).split(':', 1)[1])
    except Exception:
        return None


def test_snapshot_selects_team_matches_next_latest_and_counts():
    now = datetime(2026, 8, 28, 12, 0)
    rows = [
        {"home_source": "team:1", "away_source": "team:2", "scheduled_start": (now-timedelta(hours=2)).isoformat(), "home_score": 2, "away_score": 1},
        {"home_source": "team:3", "away_source": "team:1", "scheduled_start": (now-timedelta(hours=1)).isoformat(), "home_score": 0, "away_score": 0},
        {"home_source": "team:1", "away_source": "team:4", "scheduled_start": (now+timedelta(minutes=45)).isoformat(), "home_score": None, "away_score": None},
        {"home_source": "team:9", "away_source": "team:10", "scheduled_start": now.isoformat(), "home_score": None, "away_score": None},
    ]
    snap = build_favorite_team_snapshot(rows, 1, now=now, source_team_id=source_team_id, row_value=row_value)
    assert len(snap["matches"]) == 3
    assert snap["played_count"] == 2
    assert snap["wins"] == 1
    assert snap["latest_match"]["away_source"] == "team:1"
    assert snap["next_match"]["away_source"] == "team:4"


def test_snapshot_tolerates_invalid_dates_and_keeps_them_last():
    now = datetime(2026, 8, 28, 12, 0)
    rows = [
        {"home_source": "team:1", "away_source": "team:2", "scheduled_start": "not-a-date", "home_score": None, "away_score": None},
        {"home_source": "team:1", "away_source": "team:3", "scheduled_start": (now+timedelta(hours=1)).isoformat(), "home_score": None, "away_score": None},
    ]
    snap = build_favorite_team_snapshot(rows, 1, now=now, source_team_id=source_team_id, row_value=row_value)
    assert snap["next_match"]["away_source"] == "team:3"
    assert snap["matches"][-1]["scheduled_start"] == "not-a-date"


def test_hero_html_escapes_team_and_source_labels():
    now = datetime(2026, 8, 28, 12, 0)
    match = {"home_source": "team:1", "away_source": "team:2", "scheduled_start": (now+timedelta(minutes=30)).isoformat(), "home_score": None, "away_score": None}
    html = build_favorite_team_hero_html(
        team_name='<script>x</script>',
        snapshot={"matches": [match], "next_match": match, "latest_match": None, "played_count": 0, "wins": 0},
        now=now,
        table_position_text="1:a",
        possible_playoff=None,
        row_value=row_value,
        source_label=lambda source: '<b>Lag</b>' if source == 'team:1' else 'B',
        pitch_label=lambda match: 'Plan 1',
        swedish_datetime=lambda value: '28 aug 12:30',
    )
    assert '<script>' not in html
    assert '&lt;script&gt;x&lt;/script&gt;' in html
    assert '<b>Lag</b>' not in html
    assert '&lt;b&gt;Lag&lt;/b&gt;' in html
    assert 'om 30 min' in html


def test_app_uses_public_team_follow_module():
    app = open('app.py', encoding='utf-8').read()
    view = open('cupnavi_core/public_team_follow_view.py', encoding='utf-8').read()
    assert 'from cupnavi_core.public_team_follow_view import render_public_team_follow' in app
    assert 'render_public_team_follow(' in app
    assert 'favorite_snapshot = build_favorite_team_snapshot(' in view
    assert 'build_favorite_team_hero_html(' in view
