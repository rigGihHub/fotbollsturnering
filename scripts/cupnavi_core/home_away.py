"""Ren logik för hemma/borta-balans."""

def orientation_balance_score(home_id, away_id, home_counts, away_counts):
    """
    Lägre score är bättre efter att den föreslagna matchen lagts till.
    Primärt minimeras sammanlagd hemma/borta-obalans för de två lagen,
    sekundärt den största individuella obalansen.
    """
    home_team_diff = abs(
        (home_counts.get(home_id, 0) + 1) - away_counts.get(home_id, 0)
    )
    away_team_diff = abs(
        home_counts.get(away_id, 0) - (away_counts.get(away_id, 0) + 1)
    )
    return (
        home_team_diff + away_team_diff,
        max(home_team_diff, away_team_diff),
    )
