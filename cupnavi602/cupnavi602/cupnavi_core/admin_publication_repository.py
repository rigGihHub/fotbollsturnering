"""Read-only publication snapshots for the admin UI."""

from __future__ import annotations


def fetch_lifecycle_match_counts(one_row, tournament_id: int):
    """Return published scheduled/played match counts in one query."""
    return one_row(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 ELSE 0 END) AS played "
        "FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL AND schedule_published=1",
        (int(tournament_id),),
    )
