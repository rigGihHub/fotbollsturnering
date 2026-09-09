from __future__ import annotations


def recommend_matchcamp_matches_per_team(*, team_count: int, available_minutes: int, match_minutes: int, target_utilization: float = 0.82) -> dict:
    """Recommend a practical match target without overfilling the available pitch time.

    The recommendation deliberately leaves headroom for rest, delays and schedule balancing.
    """
    teams = max(2, int(team_count or 2))
    available = max(0, int(available_minutes or 0))
    match_len = max(1, int(match_minutes or 1))
    usable = int(available * max(0.50, min(float(target_utilization), 0.95)))

    best = 1
    for matches_per_team in range(1, 13):
        estimated_matches = (teams * matches_per_team + 1) // 2
        if estimated_matches * match_len <= usable:
            best = matches_per_team
        else:
            break

    # A matchcamp with only one match/team is technically possible but usually not useful.
    # Keep the recommendation honest when capacity is genuinely that tight.
    estimated_matches = max(1, (teams * best + 1) // 2)
    required = estimated_matches * match_len
    utilization = int(round((required / available) * 100)) if available else 999
    margin = max(0, available - required)
    return {
        "matches_per_team": best,
        "estimated_matches": estimated_matches,
        "required_minutes": required,
        "available_minutes": available,
        "utilization_percent": utilization,
        "margin_minutes": margin,
        "fits": required <= available,
    }
