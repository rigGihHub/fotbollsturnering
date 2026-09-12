"""Domain rules for result-driven playoff progression.

CupNavi keeps playoff participants symbolic (``winner:<match_id>`` / ``loser:<match_id>``)
and derives the actual team from the source result. This module validates whether a
reported result is decisive enough to advance those dependencies without mutating the
symbolic bracket provenance.
"""
from __future__ import annotations

from dataclasses import dataclass

from .playoff_dependency_safety import winner_side


@dataclass(frozen=True)
class PreparedPlayoffResult:
    home_score: int
    away_score: int
    home_penalties: int | None
    away_penalties: int | None
    winner_side: str | None
    decided_winner_id: int | None
    outcome_resolved: bool


def _score(value, label: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} måste vara ett heltal") from exc
    if number < 0:
        raise ValueError(f"{label} kan inte vara negativt")
    return number


def _optional_score(value, label: str) -> int | None:
    if value is None or value == "":
        return None
    return _score(value, label)


def prepare_result(
    *,
    stage: str | None,
    home_score,
    away_score,
    home_penalties=None,
    away_penalties=None,
    home_team_id: int | None = None,
    away_team_id: int | None = None,
) -> PreparedPlayoffResult:
    """Validate a result and derive its decisive winner when possible.

    Group matches never carry penalty or decided-winner state. Knockout matches with a
    tied regular result must include a complete, unequal penalty result before CupNavi
    treats the outcome as resolved. The client never supplies the winning team id; it is
    derived from the resolved participants and the score.
    """
    hs = _score(home_score, "Hemmamål")
    aws = _score(away_score, "Bortamål")
    hp = _optional_score(home_penalties, "Hemmastraffar")
    ap = _optional_score(away_penalties, "Bortastraffar")
    is_group = str(stage or "").strip() == "Gruppspel"

    if is_group:
        return PreparedPlayoffResult(hs, aws, None, None, None, None, True)

    if hs != aws:
        side = "home" if hs > aws else "away"
        team_id = home_team_id if side == "home" else away_team_id
        return PreparedPlayoffResult(hs, aws, None, None, side, team_id, True)

    if hp is None and ap is None:
        return PreparedPlayoffResult(hs, aws, None, None, None, None, False)
    if hp is None or ap is None:
        raise ValueError("Fyll i både hemma- och bortastraffar")
    if hp == ap:
        raise ValueError("Straffresultatet måste avgöra matchen")

    side = winner_side(
        home_score=hs,
        away_score=aws,
        home_penalties=hp,
        away_penalties=ap,
    )
    team_id = home_team_id if side == "home" else away_team_id if side == "away" else None
    return PreparedPlayoffResult(hs, aws, hp, ap, side, team_id, side is not None)


def decided_side_from_team_id(
    decided_winner_id,
    *,
    home_team_id: int | None,
    away_team_id: int | None,
) -> str | None:
    """Translate persisted decided winner identity back to a stable side."""
    if decided_winner_id is None:
        return None
    try:
        value = int(decided_winner_id)
    except (TypeError, ValueError):
        return None
    if home_team_id is not None and value == int(home_team_id):
        return "home"
    if away_team_id is not None and value == int(away_team_id):
        return "away"
    return None
