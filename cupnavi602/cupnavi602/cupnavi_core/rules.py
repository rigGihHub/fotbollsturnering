"""Testbar domänlogik för CupNavi.

Håll funktionerna här fria från Streamlit och databasåtkomst så att de kan
enhetstestas snabbt i CI.
"""

def validate_match_event_totals(team_goals: int, player_goals: int, assists: int) -> dict:
    """Validera mål/assist mot ett lags resultat i en enskild match."""
    team_goals = int(team_goals or 0)
    player_goals = int(player_goals or 0)
    assists = int(assists or 0)
    errors = []
    if min(team_goals, player_goals, assists) < 0:
        errors.append("Mål och assist kan inte vara negativa.")
    if player_goals > team_goals:
        errors.append(
            f"Laget gjorde {team_goals} mål men {player_goals} spelarmål har registrerats."
        )
    if assists > team_goals:
        errors.append(
            f"Laget gjorde {team_goals} mål, så högst {team_goals} assist kan registreras."
        )
    return {"ok": not errors, "errors": errors}


def round_robin_match_count(team_count: int) -> int:
    """Antal matcher i enkelserie där alla möter alla en gång."""
    team_count = int(team_count)
    if team_count < 0:
        raise ValueError("team_count måste vara >= 0")
    return team_count * (team_count - 1) // 2


def playoff_extra_minutes(tie_rule: str, extra_time_minutes: int) -> int:
    """Extra schematid för en slutspelsmatch."""
    return max(0, int(extra_time_minutes or 0)) if tie_rule == "Förlängning + straffar" else 0
