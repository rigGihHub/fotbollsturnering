"""Sport-neutral match format and scoring rules for CupNavi.

The database/UI may keep legacy football-oriented column names for compatibility,
but new domain logic should ask this module how a sport is structured.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .sports import sport_id


@dataclass(frozen=True)
class MatchFormat:
    sport_id: str
    participant_type: str
    segment_kind: str
    segment_count: int
    scoring_mode: str
    supports_draw: bool
    supports_overtime: bool
    supports_shootout: bool
    tracks_goals: bool
    tracks_assists: bool
    discipline_mode: str
    win_condition: str


_FORMATS = {
    "football": MatchFormat("football", "team", "half", 2, "aggregate", True, True, True, True, True, "cards", "higher_score"),
    "floorball": MatchFormat("floorball", "team", "period", 3, "aggregate", True, True, True, True, True, "penalty_minutes", "higher_score"),
    "handball": MatchFormat("handball", "team", "half", 2, "aggregate", True, True, True, True, False, "two_minute_and_cards", "higher_score"),
    "ice_hockey": MatchFormat("ice_hockey", "team", "period", 3, "aggregate", True, True, True, True, True, "penalty_minutes", "higher_score"),
    "basketball": MatchFormat("basketball", "team", "quarter", 4, "aggregate", False, True, False, False, False, "fouls", "higher_score"),
    "volleyball": MatchFormat("volleyball", "team", "set", 5, "set_based", False, False, False, False, False, "none", "sets_won"),
    "tennis": MatchFormat("tennis", "individual_or_pair", "set", 3, "set_based", False, False, False, False, False, "none", "sets_won"),
    "padel": MatchFormat("padel", "pair", "set", 3, "set_based", False, False, False, False, False, "none", "sets_won"),
    "other": MatchFormat("other", "configurable", "period", 2, "aggregate", True, False, False, False, False, "none", "higher_score"),
}


def match_format(sport: str | None) -> MatchFormat:
    return _FORMATS[sport_id(sport)]


def score_model(sport: str | None) -> dict[str, object]:
    fmt = match_format(sport)
    return {
        "sport_id": fmt.sport_id,
        "participant_type": fmt.participant_type,
        "segment_kind": fmt.segment_kind,
        "segment_count": fmt.segment_count,
        "scoring_mode": fmt.scoring_mode,
        "supports_draw": fmt.supports_draw,
        "supports_overtime": fmt.supports_overtime,
        "supports_shootout": fmt.supports_shootout,
        "tracks_goals": fmt.tracks_goals,
        "tracks_assists": fmt.tracks_assists,
        "discipline_mode": fmt.discipline_mode,
        "win_condition": fmt.win_condition,
    }


def validate_segment_scores(sport: str | None, segments: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Validate generic per-segment scores without knowing Streamlit/database details."""
    fmt = match_format(sport)
    errors: list[str] = []
    normalized: list[dict[str, int]] = []
    for index, segment in enumerate(segments, 1):
        try:
            home = int(segment.get("home", 0))
            away = int(segment.get("away", 0))
        except (TypeError, ValueError):
            errors.append(f"Segment {index} har ogiltigt resultat.")
            continue
        if home < 0 or away < 0:
            errors.append(f"Segment {index} kan inte ha negativa poäng.")
            continue
        if fmt.scoring_mode == "set_based" and home == away:
            errors.append(f"Segment {index} måste ha en vinnare i setbaserad poängräkning.")
            continue
        normalized.append({"home": home, "away": away})

    if fmt.scoring_mode == "set_based" and len(normalized) > fmt.segment_count:
        errors.append(f"Högst {fmt.segment_count} set får registreras för sporten.")

    return {"ok": not errors, "errors": errors, "segments": normalized}


def aggregate_result(sport: str | None, segments: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Return the scoreboard result for aggregate- and set-based sports."""
    validation = validate_segment_scores(sport, segments)
    if not validation["ok"]:
        return {"ok": False, "errors": validation["errors"]}
    fmt = match_format(sport)
    rows = validation["segments"]
    if fmt.scoring_mode == "set_based":
        home = sum(1 for row in rows if row["home"] > row["away"])
        away = sum(1 for row in rows if row["away"] > row["home"])
    else:
        home = sum(row["home"] for row in rows)
        away = sum(row["away"] for row in rows)
    return {"ok": True, "home": home, "away": away, "mode": fmt.scoring_mode}
