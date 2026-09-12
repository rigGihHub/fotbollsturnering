"""Pure structural schedule dependencies for CupNavi knockout brackets.

CupNavi already persists bracket_id, round_no and match_no on matches. Until
participant source strings have a canonical machine-readable contract, v644 uses
only that persisted structure and never guesses from free-text placeholders.
"""
from __future__ import annotations


def _positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def structural_playoff_dependencies(matches: list[dict]) -> dict[int, tuple[int, ...]]:
    """Return direct upstream knockout match ids keyed by downstream match id.

    For the established ascending knockout round convention, match N in round R
    is fed by matches 2N-1 and 2N in round R-1 within the same bracket. We only
    emit dependencies that actually exist in the persisted bracket. If no such
    rows exist, no dependency is invented; this keeps legacy/free-text playoff
    data safe until it is migrated to an explicit participant-source contract.
    """
    by_slot: dict[tuple[int, int, int], int] = {}
    normalized: list[tuple[int, int, int, int]] = []
    for row in matches:
        bracket_id = _positive_int(row.get("bracket_id"))
        round_no = _positive_int(row.get("round_no"))
        match_no = _positive_int(row.get("match_no"))
        match_id = _positive_int(row.get("id"))
        if None in (bracket_id, round_no, match_no, match_id):
            continue
        by_slot[(bracket_id, round_no, match_no)] = match_id
        normalized.append((match_id, bracket_id, round_no, match_no))

    result: dict[int, tuple[int, ...]] = {}
    for match_id, bracket_id, round_no, match_no in normalized:
        if round_no <= 1:
            continue
        upstream: list[int] = []
        for previous_match_no in (2 * match_no - 1, 2 * match_no):
            upstream_id = by_slot.get((bracket_id, round_no - 1, previous_match_no))
            if upstream_id is not None:
                upstream.append(upstream_id)
        if upstream:
            result[match_id] = tuple(sorted(upstream))
    return result
