from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable


def fetch_admin_workflow_counts(
    query_one: Callable[[str, tuple[Any, ...]], Any],
    tournament_id: int,
    *,
    now: datetime | None = None,
) -> Any:
    """Fetch the admin overview counters in one database round-trip.

    The caller owns connection/performance accounting and caching; this module owns
    only the stable query contract used by the admin overview and instructions view.
    """
    current = now or datetime.now()
    now_iso = current.isoformat(timespec="seconds")
    delayed_cutoff_iso = (current - timedelta(minutes=90)).isoformat(timespec="seconds")
    tid = int(tournament_id)
    return query_one(
        """SELECT
          (SELECT COUNT(*) FROM teams WHERE tournament_id=?) AS teams_n,
          (SELECT COUNT(*) FROM groups WHERE tournament_id=?) AS groups_n,
          (SELECT COUNT(*) FROM players p JOIN teams t ON t.id=p.team_id WHERE t.tournament_id=?) AS players_n,
          (SELECT COUNT(*) FROM referees WHERE tournament_id=?) AS refs_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=?) AS matches_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL) AS scheduled_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL) AS played_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND referee_id IS NULL) AS missing_refs_n,
          (SELECT COUNT(*) FROM teams WHERE tournament_id=? AND COALESCE(checked_in,0)=0) AS unchecked_n,
          (SELECT COUNT(*) FROM pitches WHERE tournament_id=?) AS pitches_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND schedule_published=1) AS published_n,
          (SELECT COUNT(*) FROM player_match_stats s JOIN matches m ON m.id=s.match_id
             WHERE m.tournament_id=? AND (s.goals>0 OR s.assists>0 OR s.yellow_cards>0 OR s.red_cards>0)) AS events_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start>?) AS upcoming_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND scheduled_start<=?
             AND (home_score IS NULL OR away_score IS NULL)) AS missing_results_n,
          (SELECT COUNT(*) FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND scheduled_start<?
             AND (home_score IS NULL OR away_score IS NULL)) AS delayed_n
        """,
        (
            tid, tid, tid, tid, tid, tid, tid, tid, tid, tid, tid, tid,
            tid, now_iso, tid, now_iso, tid, delayed_cutoff_iso,
        ),
    )
