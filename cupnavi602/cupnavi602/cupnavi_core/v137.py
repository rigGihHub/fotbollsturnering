"""Pure helpers for CupNavi v137 scheduling, travel and notifications."""
from __future__ import annotations

VALID_SCHEDULE_STRATEGIES = {"earliest_finish", "use_pitch_windows"}


def normalize_schedule_strategy(value: object) -> str:
    value = str(value or "").strip()
    return value if value in VALID_SCHEDULE_STRATEGIES else "earliest_finish"


def candidate_sort_key(candidate, strategy: str, pitch_loads: dict[int, int] | None = None):
    """Return deterministic objective key for a scheduler candidate.

    Candidate tuple: (start, consecutive_penalty, late_penalty, order, pitch, referee).
    earliest_finish minimizes time first. use_pitch_windows balances pitch utilization
    first, then soft constraints and time. This changes the scheduling objective rather
    than only changing UI text.
    """
    start, consecutive, late, order, pitch, referee = candidate
    loads = pitch_loads or {}
    strategy = normalize_schedule_strategy(strategy)
    if strategy == "use_pitch_windows":
        return (int(consecutive), int(late), int(loads.get(int(pitch), 0)), start, int(order), int(pitch), int(referee or 0))
    return (int(consecutive), int(late), start, int(order), int(pitch), int(referee or 0))


def travel_minutes(matrix: dict[tuple[int, int], int] | None, from_pitch: int | None, to_pitch: int | None) -> int:
    if not matrix or not from_pitch or not to_pitch or int(from_pitch) == int(to_pitch):
        return 0
    return max(0, int(matrix.get((int(from_pitch), int(to_pitch)), matrix.get((int(to_pitch), int(from_pitch)), 0)) or 0))
