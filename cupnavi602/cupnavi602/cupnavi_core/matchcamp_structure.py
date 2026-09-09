"""Preview-first match-structure balancing for Matchcamp.

This module never writes to the database. It may rewire only direct-team,
unplayed, unlocked group matches. Match rows, time slots, pitches and referees
stay intact; only the two team sources can change. The proposal is accepted
only when structural balance improves without worsening overlaps or short rest.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from cupnavi_core.schedule_improvement import schedule_flow_metrics


def _team_id(source):
    text = str(source or "")
    if not text.startswith("team:"):
        return None
    try:
        return int(text.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


def _pair(home_id, away_id):
    if home_id is None or away_id is None:
        return None
    return tuple(sorted((int(home_id), int(away_id))))


def matchcamp_structure_metrics(matches, teams, *, match_duration_minutes):
    """Measure match-count balance and repeated opponents within each group."""
    group_teams: dict[int, list[int]] = defaultdict(list)
    for team in teams:
        gid = team.get("group_id")
        if gid is not None:
            group_teams[int(gid)].append(int(team["id"]))

    counts = Counter()
    pair_counts = Counter()
    for row in matches:
        if row.get("stage") != "Gruppspel":
            continue
        home = _team_id(row.get("home_source"))
        away = _team_id(row.get("away_source"))
        gid = row.get("group_id")
        if home is None or away is None or gid is None or home == away:
            continue
        counts[(int(gid), home)] += 1
        counts[(int(gid), away)] += 1
        pair_counts[(int(gid), _pair(home, away))] += 1

    group_spreads = {}
    total_range = 0
    max_spread = 0
    total_abs_deviation = 0
    for gid, team_ids in group_teams.items():
        if not team_ids:
            continue
        values = [counts[(gid, tid)] for tid in team_ids]
        spread = max(values) - min(values)
        group_spreads[gid] = spread
        max_spread = max(max_spread, spread)
        total_range += spread
        # Integer-friendly balance penalty around the group's average.
        total_matches_for_teams = sum(values)
        n = len(values)
        total_abs_deviation += sum(abs(v * n - total_matches_for_teams) for v in values)

    repeated_pairs = sum(max(0, n - 1) for n in pair_counts.values())
    duration = max(1, int(match_duration_minutes or 1))
    playtime_spread_minutes = max_spread * duration

    # Match-count balance has highest priority. Repeats are second.
    objective = total_abs_deviation * 100 + total_range * 50 + repeated_pairs * 25

    return {
        "match_count_spread": max_spread,
        "playtime_spread_minutes": playtime_spread_minutes,
        "repeated_opponents": repeated_pairs,
        "group_spreads": group_spreads,
        "balance_penalty": total_abs_deviation,
        "objective": objective,
    }


def build_matchcamp_structure_improvement(
    matches,
    teams,
    *,
    match_duration_minutes,
    minimum_rest_minutes,
    protected_team_ids=(),
    max_passes=8,
):
    """Return a deterministic opponent-rewiring proposal.

    Safety rules:
    - only direct-team, group-stage, unplayed, unlocked rows may change;
    - protected teams are never removed from or added to a changed row;
    - candidate teams must belong to the same group;
    - no self-match is allowed;
    - time, pitch and referee stay unchanged;
    - overlaps and short-rest counts may not worsen;
    - only a strict structural improvement is accepted.
    """
    protected = {int(x) for x in (protected_team_ids or ())}
    working = [dict(row) for row in matches]
    original = [dict(row) for row in matches]

    teams_by_group: dict[int, list[int]] = defaultdict(list)
    for team in teams:
        gid = team.get("group_id")
        if gid is not None:
            teams_by_group[int(gid)].append(int(team["id"]))
    for gid in teams_by_group:
        teams_by_group[gid] = sorted(set(teams_by_group[gid]))

    eligible = []
    for idx, row in enumerate(working):
        home = _team_id(row.get("home_source"))
        away = _team_id(row.get("away_source"))
        gid = row.get("group_id")
        if (
            row.get("stage") == "Gruppspel"
            and gid is not None
            and not bool(row.get("schedule_locked"))
            and row.get("home_score") is None
            and row.get("away_score") is None
            and home is not None
            and away is not None
            and home not in protected
            and away not in protected
        ):
            eligible.append(idx)

    before = matchcamp_structure_metrics(
        working, teams, match_duration_minutes=match_duration_minutes
    )
    timing_before = schedule_flow_metrics(
        working,
        match_duration_minutes=match_duration_minutes,
        minimum_rest_minutes=minimum_rest_minutes,
        arrangement_type="matchcamp",
    )

    best = before
    improved_any = False

    for _ in range(max(1, int(max_passes))):
        improved_this_pass = False
        for idx in eligible:
            row = working[idx]
            gid = int(row["group_id"])
            old_home = _team_id(row.get("home_source"))
            old_away = _team_id(row.get("away_source"))
            if old_home is None or old_away is None:
                continue

            candidates = [tid for tid in teams_by_group.get(gid, []) if tid not in protected]
            # Try changing one endpoint at a time. This keeps the search explainable
            # and avoids large, hard-to-review rewrites.
            attempts = []
            for candidate in candidates:
                if candidate != old_away and candidate != old_home:
                    attempts.append((candidate, old_away))
                if candidate != old_home and candidate != old_away:
                    attempts.append((old_home, candidate))

            accepted = False
            for new_home, new_away in attempts:
                if new_home == new_away:
                    continue
                prev_home_source = row.get("home_source")
                prev_away_source = row.get("away_source")
                row["home_source"] = f"team:{new_home}"
                row["away_source"] = f"team:{new_away}"

                metric = matchcamp_structure_metrics(
                    working, teams, match_duration_minutes=match_duration_minutes
                )
                timing = schedule_flow_metrics(
                    working,
                    match_duration_minutes=match_duration_minutes,
                    minimum_rest_minutes=minimum_rest_minutes,
                    arrangement_type="matchcamp",
                )
                safe_timing = (
                    timing["overlap"] <= timing_before["overlap"]
                    and timing["short_rest"] <= timing_before["short_rest"]
                )
                if safe_timing and metric["objective"] < best["objective"]:
                    best = metric
                    timing_before = timing
                    improved_any = True
                    improved_this_pass = True
                    accepted = True
                    break

                row["home_source"] = prev_home_source
                row["away_source"] = prev_away_source

            if accepted:
                continue
        if not improved_this_pass:
            break

    updates = []
    if improved_any:
        for old, new in zip(original, working):
            if (
                old.get("home_source") != new.get("home_source")
                or old.get("away_source") != new.get("away_source")
            ):
                updates.append({
                    "id": int(new["id"]),
                    "expected_home_source": old.get("home_source"),
                    "expected_away_source": old.get("away_source"),
                    "home_source": new.get("home_source"),
                    "away_source": new.get("away_source"),
                    "group_id": int(new["group_id"]),
                })

    after = (
        matchcamp_structure_metrics(
            working, teams, match_duration_minutes=match_duration_minutes
        )
        if updates
        else before
    )
    return {
        "before": before,
        "after": after,
        "updates": updates,
        "eligible_count": len(eligible),
        "improved": bool(updates) and after["objective"] < before["objective"],
    }
