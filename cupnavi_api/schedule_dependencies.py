"""Schedule dependencies for CupNavi participant sources and knockout brackets."""
from __future__ import annotations

from cupnavi_core.participant_sources import parse_participant_source


def _positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def structural_playoff_dependencies(matches: list[dict]) -> dict[int, tuple[int, ...]]:
    """Return fallback knockout dependencies from persisted bracket structure."""
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


def participant_source_dependencies(matches: list[dict]) -> dict[int, tuple[int, ...]]:
    """Return explicit upstream match ids from canonical participant sources.

    ``winner``/``loser`` reference one exact match. ``group`` conservatively
    depends on every group-stage match in the referenced group, because the
    qualifying team and its safe rest window are not final before group play is
    complete. Legacy text creates no dependency.
    """
    rows_by_id = {
        int(row["id"]): row
        for row in matches
        if _positive_int(row.get("id")) is not None
    }
    group_matches: dict[int, list[int]] = {}
    for row in matches:
        group_id = _positive_int(row.get("group_id"))
        match_id = _positive_int(row.get("id"))
        stage = str(row.get("stage") or "").strip().casefold()
        if group_id is None or match_id is None or stage != "gruppspel":
            continue
        group_matches.setdefault(group_id, []).append(match_id)

    result: dict[int, tuple[int, ...]] = {}
    for row in matches:
        downstream_id = _positive_int(row.get("id"))
        if downstream_id is None:
            continue
        upstream: set[int] = set()
        has_explicit_dependency_source = False
        for raw_source in (row.get("home_source"), row.get("away_source")):
            source = parse_participant_source(raw_source)
            if not source.is_dependency:
                continue
            has_explicit_dependency_source = True
            if source.kind in {"winner", "loser"}:
                if source.source_id in rows_by_id and source.source_id != downstream_id:
                    upstream.add(int(source.source_id))
            elif source.kind == "group" and source.source_id is not None:
                upstream.update(
                    match_id
                    for match_id in group_matches.get(int(source.source_id), ())
                    if match_id != downstream_id
                )
        if has_explicit_dependency_source:
            result[downstream_id] = tuple(sorted(upstream))
    return result


def schedule_dependencies(matches: list[dict]) -> dict[int, tuple[int, ...]]:
    """Prefer canonical source dependencies; use v644 structure only as fallback.

    A match that contains an explicit dependency source is never supplemented by
    guessed structural participants. This is important for loser paths such as
    bronze matches, which do not necessarily mirror winner-bracket structure.
    """
    explicit = participant_source_dependencies(matches)
    structural = structural_playoff_dependencies(matches)
    result = dict(structural)
    result.update(explicit)
    return result


def dependency_depths(matches: list[dict]) -> dict[int, int]:
    """Return cycle-safe dependency depth for deterministic proposal ordering."""
    dependencies = schedule_dependencies(matches)
    memo: dict[int, int] = {}

    def depth(match_id: int, visiting: set[int]) -> int:
        if match_id in memo:
            return memo[match_id]
        if match_id in visiting:
            return 0
        visiting = {*visiting, match_id}
        value = 0
        for upstream_id in dependencies.get(match_id, ()):
            value = max(value, 1 + depth(upstream_id, visiting))
        memo[match_id] = value
        return value

    for row in matches:
        match_id = _positive_int(row.get("id"))
        if match_id is not None:
            depth(match_id, set())
    return memo
