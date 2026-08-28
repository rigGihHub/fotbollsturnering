"""Push-notification readiness helpers.

This module deliberately does not send web push yet. It creates a durable,
provider-neutral outbox that a future service worker/VAPID delivery worker can
consume without coupling CupNavi's match reporting to a specific push vendor.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def goal_push_events(*, match_id: int, tournament_id: int,
                     home_team_id: int | None, away_team_id: int | None,
                     home_team_name: str, away_team_name: str,
                     old_home_score: int | None, old_away_score: int | None,
                     new_home_score: int | None, new_away_score: int | None) -> list[dict]:
    """Return push events only for score increases.

    A correction that lowers a score never creates a push event. A jump of more
    than one goal produces one event for the latest score state, avoiding a burst
    of stale notifications after bulk/final-result entry.
    """
    if new_home_score is None or new_away_score is None:
        return []
    old_h = int(old_home_score or 0)
    old_a = int(old_away_score or 0)
    new_h = int(new_home_score)
    new_a = int(new_away_score)
    events: list[dict] = []

    def add(team_id: int | None, team_name: str, side: str, score: int):
        if not team_id:
            return
        title = f"⚽ Mål för {team_name}!"
        body = f"{home_team_name}–{away_team_name} {new_h}–{new_a}"
        events.append({
            "tournament_id": int(tournament_id),
            "team_id": int(team_id),
            "match_id": int(match_id),
            "event_type": "goal",
            "event_key": f"goal:{match_id}:{side}:{score}",
            "title": title,
            "body": body,
            "payload": {
                "type": "goal",
                "match_id": int(match_id),
                "team_id": int(team_id),
                "score": {"home": new_h, "away": new_a},
            },
        })

    if new_h > old_h:
        add(home_team_id, home_team_name, "home", new_h)
    if new_a > old_a:
        add(away_team_id, away_team_name, "away", new_a)
    return events


def enqueue_push_event(con, event: dict) -> bool:
    """Insert one idempotent push event into the durable outbox."""
    cur = con.execute(
        """INSERT OR IGNORE INTO push_notification_outbox(
               tournament_id,team_id,match_id,event_type,event_key,title,body,payload_json,
               created_at,status)
           VALUES(?,?,?,?,?,?,?,?,?,'pending')""",
        (
            int(event["tournament_id"]), int(event["team_id"]), int(event["match_id"]),
            str(event["event_type"]), str(event["event_key"]), str(event["title"]),
            str(event["body"]), json.dumps(event.get("payload") or {}, ensure_ascii=False,
                                           separators=(",", ":")), now_iso(),
        ),
    )
    return bool(cur.rowcount)


def enqueue_goal_push_events(con, **kwargs) -> int:
    return sum(1 for event in goal_push_events(**kwargs) if enqueue_push_event(con, event))
