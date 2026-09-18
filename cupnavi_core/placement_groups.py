"""Pure competition logic for CupNavi placement groups.

A placement-group phase is a second round-robin stage where teams finishing in
the same position in different preliminary groups meet each other. The module is
storage agnostic so admin, scheduling and public views can share one contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


PLACEMENT_GROUP_STAGE = "Placeringsgrupp"


@dataclass(frozen=True)
class PlacementGroup:
    placement: int
    name: str
    sources: tuple[str, ...]
    overall_start: int
    overall_end: int

    def as_dict(self) -> dict:
        return {
            "placement": self.placement,
            "name": self.name,
            "sources": list(self.sources),
            "overall_start": self.overall_start,
            "overall_end": self.overall_end,
        }


def _positive_int(value) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def build_placement_groups(groups: list[dict], *, max_placement: int | None = None) -> list[dict]:
    """Build placement groups from preliminary group metadata.

    Each input group needs ``id`` and either ``team_count`` or a ``teams`` list.
    A placement group is emitted only when at least two preliminary groups have a
    team at that placement. This also makes uneven preliminary groups safe: a
    short group simply contributes no source to lower placement groups.
    """
    normalized: list[tuple[int, int]] = []
    for group in groups:
        group_id = _positive_int(group.get("id"))
        team_count = _positive_int(group.get("team_count"))
        if team_count is None and isinstance(group.get("teams"), (list, tuple)):
            team_count = len(group["teams"])
        if group_id is not None and team_count is not None:
            normalized.append((group_id, team_count))

    if len(normalized) < 2:
        return []

    highest = max(count for _, count in normalized)
    if max_placement is not None:
        requested = _positive_int(max_placement)
        highest = min(highest, requested or 0)

    result: list[dict] = []
    overall_start = 1
    for placement in range(1, highest + 1):
        sources = tuple(
            f"group:{group_id}:{placement}"
            for group_id, team_count in normalized
            if team_count >= placement
        )
        if len(sources) < 2:
            continue
        overall_end = overall_start + len(sources) - 1
        result.append(
            PlacementGroup(
                placement=placement,
                name=f"Placeringsgrupp {placement}",
                sources=sources,
                overall_start=overall_start,
                overall_end=overall_end,
            ).as_dict()
        )
        overall_start = overall_end + 1
    return result


def build_placement_group_matches(placement_group: dict) -> list[dict]:
    """Return one round-robin meeting for every participant pair."""
    sources = tuple(str(value) for value in placement_group.get("sources", ()) if value)
    placement = _positive_int(placement_group.get("placement"))
    if placement is None or len(sources) < 2:
        return []
    return [
        {
            "stage": PLACEMENT_GROUP_STAGE,
            "placement_group": placement,
            "home_source": home,
            "away_source": away,
        }
        for home, away in combinations(sources, 2)
    ]


def overall_ranking(placement_groups: list[dict], standings_by_placement: dict[int, list]) -> list[dict]:
    """Flatten final placement-group tables into a tournament-wide ranking.

    Ranking is intentionally hierarchical: a team in Placeringsgrupp 2 can never
    pass a team from Placeringsgrupp 1 because goal difference happened to be
    better. ``standings_by_placement`` must already be ordered by the tournament's
    normal table tie-break rules.
    """
    ranked: list[dict] = []
    overall_position = 1
    for group in sorted(placement_groups, key=lambda item: int(item["placement"])):
        placement = int(group["placement"])
        for local_position, team in enumerate(standings_by_placement.get(placement, ()), start=1):
            ranked.append({
                "position": overall_position,
                "placement_group": placement,
                "placement_group_position": local_position,
                "team": team,
            })
            overall_position += 1
    return ranked
