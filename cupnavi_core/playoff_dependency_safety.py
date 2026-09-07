"""Safety rules for correcting playoff source results.

A downstream playoff match may reference ``winner:<match_id>`` or
``loser:<match_id>``. Once that downstream match has started, has a result, or
has player events, changing the upstream outcome must never silently replace
its participant.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class PlayoffDependencyImpact:
    blocked: bool
    downstream_match_ids: tuple[int, ...] = ()
    reason: str = ""


def winner_side(
    *,
    home_score: Any,
    away_score: Any,
    home_penalties: Any = None,
    away_penalties: Any = None,
    decided_winner_side: str | None = None,
) -> str | None:
    """Return ``home``/``away`` when the outcome is knowable, else ``None``."""
    if decided_winner_side in {"home", "away"}:
        return decided_winner_side
    if home_score is None or away_score is None:
        return None
    home_score = int(home_score)
    away_score = int(away_score)
    if home_score > away_score:
        return "home"
    if away_score > home_score:
        return "away"
    if home_penalties is None or away_penalties is None:
        return None
    home_penalties = int(home_penalties)
    away_penalties = int(away_penalties)
    if home_penalties > away_penalties:
        return "home"
    if away_penalties > home_penalties:
        return "away"
    return None


def downstream_is_locked(row: Any, *, row_value: Callable[[Any, str, Any], Any]) -> bool:
    status = str(row_value(row, "match_status", "not_started") or "not_started").strip().lower()
    if status not in {"", "not_started"}:
        return True
    if row_value(row, "home_score", None) is not None or row_value(row, "away_score", None) is not None:
        return True
    if int(row_value(row, "event_count", 0) or 0) > 0:
        return True
    return False





def recovery_eligibility(
    row: Any,
    *,
    row_value: Callable[[Any, str, Any], Any],
) -> tuple[bool, str]:
    """Return whether a downstream match may be safely reset before upstream correction."""
    status = str(row_value(row, "match_status", "not_started") or "not_started").strip().lower()
    actual_started_at = str(row_value(row, "actual_started_at", "") or "").strip()
    event_count = int(row_value(row, "event_count", 0) or 0)

    if status not in {"", "not_started"}:
        return False, "Matchen har redan startat eller avslutats."
    if actual_started_at:
        return False, "Matchen har en registrerad faktisk starttid."
    if event_count:
        return False, "Matchen har registrerade matchhändelser."
    return True, "Matchen har inte startat och saknar matchhändelser."


def build_dependency_guidance(
    rows: Iterable[Any],
    *,
    row_value: Callable[[Any, str, Any], Any],
) -> tuple[str, ...]:
    """Create concise organizer-facing explanations for locked downstream matches."""
    messages = []
    for row in rows:
        match_id = int(row_value(row, "id", 0) or 0)
        stage = str(row_value(row, "stage", "Slutspel") or "Slutspel")
        match_no = row_value(row, "match_no", None)
        scheduled_start = str(row_value(row, "scheduled_start", "") or "").strip()
        status = str(row_value(row, "match_status", "not_started") or "not_started").strip().lower()
        home_score = row_value(row, "home_score", None)
        away_score = row_value(row, "away_score", None)
        event_count = int(row_value(row, "event_count", 0) or 0)

        label = stage
        if match_no is not None:
            label += f" #{int(match_no)}"
        if match_id:
            label += f" (match {match_id})"

        reasons = []
        if status not in {"", "not_started"}:
            reasons.append("matchen har startat")
        if home_score is not None or away_score is not None:
            reasons.append("resultat finns")
        if event_count:
            reasons.append("matchhändelser finns")
        if scheduled_start:
            reasons.append(f"avspark {scheduled_start.replace('T', ' ')[:16]}")

        reason_text = " · ".join(reasons) if reasons else "matchen används redan"
        messages.append(
            f"{label}: {reason_text}. Återställ eller rätta den här matchen först innan föregående slutspelsresultat ändras."
        )
    return tuple(messages)



def transitive_downstream_match_ids(
    source_match_id: int,
    rows: Iterable[Any],
    *,
    row_value: Callable[[Any, str, Any], Any],
) -> tuple[int, ...]:
    """Return all descendants that depend on winner/loser of source match.

    Traversal is source-token based and cycle-safe. It deliberately follows
    both winner and loser references because bronze/consolation paths can depend
    on a losing semifinalist just as finals depend on winners.
    """
    source_match_id = int(source_match_id)
    rows = list(rows)
    by_id = {
        int(row_value(row, "id", 0) or 0): row
        for row in rows
        if int(row_value(row, "id", 0) or 0) > 0
    }
    descendants = []
    seen = {source_match_id}
    frontier = [source_match_id]

    while frontier:
        current_id = frontier.pop(0)
        wanted = {f"winner:{current_id}", f"loser:{current_id}"}
        for match_id, row in by_id.items():
            if match_id in seen:
                continue
            home_source = str(row_value(row, "home_source", "") or "")
            away_source = str(row_value(row, "away_source", "") or "")
            if home_source in wanted or away_source in wanted:
                seen.add(match_id)
                descendants.append(match_id)
                frontier.append(match_id)

    return tuple(descendants)


def dependency_impact(
    *,
    old_winner_side: str | None,
    new_winner_side: str | None,
    downstream_rows: Iterable[Any],
    row_value: Callable[[Any, str, Any], Any],
) -> PlayoffDependencyImpact:
    """Block only when the upstream winner/loser outcome changes and a dependent
    downstream match is no longer untouched.

    If either side is unknown, a changed/removed settled outcome is treated
    conservatively as an outcome change.
    """
    if old_winner_side == new_winner_side:
        return PlayoffDependencyImpact(False)

    locked_ids = tuple(
        int(row_value(row, "id", 0) or 0)
        for row in downstream_rows
        if downstream_is_locked(row, row_value=row_value)
        and int(row_value(row, "id", 0) or 0) > 0
    )
    if not locked_ids:
        return PlayoffDependencyImpact(False)

    return PlayoffDependencyImpact(
        True,
        locked_ids,
        "Resultatet kan inte ändras eftersom en senare slutspelsmatch som beror på detta resultat redan har startat eller innehåller resultat/händelser.",
    )
