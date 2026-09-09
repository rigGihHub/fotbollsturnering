"""Optional OR-Tools based schedule ordering for CupNavi.

The optimizer improves the order in which concrete matches are fed into the
existing safe scheduler. Hard constraints prevent a participant from appearing
on two pitches in the same scheduling wave. The objective minimizes adjacent
waves for the same participant and compacts the schedule. If OR-Tools is not
available, a deterministic greedy fallback preserves deployability.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Sequence


def ortools_available() -> bool:
    try:
        from ortools.sat.python import cp_model  # noqa: F401
        return True
    except Exception:
        return False


def _greedy_order(items: Sequence[tuple[object, int, int]], pitch_count: int) -> list[int]:
    remaining = list(range(len(items)))
    result: list[int] = []
    previous_teams: set[int] = set()
    while remaining:
        remaining.sort(key=lambda idx: (
            bool({items[idx][1], items[idx][2]} & previous_teams),
            idx,
        ))
        idx = remaining.pop(0)
        result.append(idx)
        previous_teams = {items[idx][1], items[idx][2]}
    return result


def optimize_match_order(items: Sequence[tuple[object, int, int]], pitch_count: int = 1, time_limit_seconds: float = 2.0) -> tuple[list[int], str]:
    """Return item indices in optimized scheduling order and engine label.

    ``items`` is ``(opaque_match, home_participant_id, away_participant_id)``.
    The returned order is safe to use as an input ordering; the existing
    scheduler remains responsible for exact times, pitch gaps, travel wishes,
    locked matches, referees and playoff dependencies.
    """
    n = len(items)
    if n <= 1:
        return list(range(n)), "trivial"
    pitch_count = max(1, int(pitch_count or 1))
    try:
        from ortools.sat.python import cp_model
    except Exception:
        return _greedy_order(items, pitch_count), "greedy-fallback"

    max_waves = n
    model = cp_model.CpModel()
    wave = [model.NewIntVar(0, max_waves - 1, f"wave_{i}") for i in range(n)]
    pitch = [model.NewIntVar(0, pitch_count - 1, f"pitch_{i}") for i in range(n)]

    # One match per pitch in a wave.
    for i in range(n):
        for j in range(i + 1, n):
            same_wave = model.NewBoolVar(f"same_wave_{i}_{j}")
            model.Add(wave[i] == wave[j]).OnlyEnforceIf(same_wave)
            model.Add(wave[i] != wave[j]).OnlyEnforceIf(same_wave.Not())
            model.Add(pitch[i] != pitch[j]).OnlyEnforceIf(same_wave)

            # Same participant can never play twice in the same wave.
            teams_i = {int(items[i][1]), int(items[i][2])}
            teams_j = {int(items[j][1]), int(items[j][2])}
            if teams_i & teams_j:
                model.Add(wave[i] != wave[j])

    last_wave = model.NewIntVar(0, max_waves - 1, "last_wave")
    model.AddMaxEquality(last_wave, wave)

    adjacency_penalties = []
    participant_matches: dict[int, list[int]] = defaultdict(list)
    for i, (_, home, away) in enumerate(items):
        participant_matches[int(home)].append(i)
        participant_matches[int(away)].append(i)
    for team_id, indexes in participant_matches.items():
        for pos, i in enumerate(indexes):
            for j in indexes[pos + 1:]:
                diff = model.NewIntVar(0, max_waves - 1, f"diff_{team_id}_{i}_{j}")
                model.AddAbsEquality(diff, wave[i] - wave[j])
                adjacent = model.NewBoolVar(f"adj_{team_id}_{i}_{j}")
                model.Add(diff == 1).OnlyEnforceIf(adjacent)
                model.Add(diff != 1).OnlyEnforceIf(adjacent.Not())
                adjacency_penalties.append(adjacent)

    model.Minimize(last_wave * 100 + sum(adjacency_penalties) * 10 + sum(wave))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.2, float(time_limit_seconds))
    solver.parameters.num_search_workers = 8
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return _greedy_order(items, pitch_count), "greedy-fallback"

    order = sorted(range(n), key=lambda i: (solver.Value(wave[i]), solver.Value(pitch[i]), i))
    return order, "ortools-cp-sat"
