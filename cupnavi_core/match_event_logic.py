"""Pure preparation logic for Matchhändelser.

No Streamlit or database access belongs here. Persistence remains in app.py
until concurrency behavior for player_match_stats has its own protected write
boundary.
"""

EVENT_FIELDS=("goals","assists","yellow_cards","red_cards")


def _int_or_zero(value, *, is_na):
    if value is None or is_na(value):
        return 0
    return max(0, int(value))


def event_values_from_editor(row, *, is_na):
    """Normalize one data-editor row to the four stored event counters."""
    return {
        "goals": _int_or_zero(row["Mål"], is_na=is_na),
        "assists": _int_or_zero(row["Assist"], is_na=is_na),
        "yellow_cards": _int_or_zero(row["Varningar"], is_na=is_na),
        "red_cards": _int_or_zero(row["Utvisningar"], is_na=is_na),
    }


def event_values_from_existing(previous):
    if previous is None:
        return {field:0 for field in EVENT_FIELDS}
    return {field:int(previous[field] or 0) for field in EVENT_FIELDS}


def prepare_changed_event_rows(edited_rows, existing_by_player_id, *, match_id, is_na):
    """Return only rows whose persisted counters actually changed."""
    changed=[]
    for row in edited_rows:
        player_id=int(row["player_id"])
        new_values=event_values_from_editor(row,is_na=is_na)
        previous_values=event_values_from_existing(existing_by_player_id.get(player_id))
        if new_values != previous_values:
            changed.append({
                "match_id":int(match_id),
                "player_id":player_id,
                **new_values,
                "expected":previous_values,
            })
    return changed


def prepare_quick_event_update(existing_by_player_id, *, match_id, player_id, field, delta):
    """Build one optimistic-locking event counter update for touch-first entry."""
    if field not in EVENT_FIELDS:
        raise ValueError(f"Unsupported event field: {field}")
    player_id=int(player_id)
    previous_values=event_values_from_existing(existing_by_player_id.get(player_id))
    new_values=dict(previous_values)
    new_values[field]=max(0, int(new_values[field]) + int(delta))
    if new_values == previous_values:
        return None
    return {
        "match_id":int(match_id),
        "player_id":player_id,
        **new_values,
        "expected":previous_values,
    }


def event_totals_after_update(existing_by_player_id, update):
    """Return team-level goal/assist totals after a candidate quick update."""
    player_id=int(update["player_id"])
    goals=0
    assists=0
    for current_player_id, previous in existing_by_player_id.items():
        values=event_values_from_existing(previous)
        if int(current_player_id) == player_id:
            values={field:int(update[field]) for field in EVENT_FIELDS}
        goals += int(values["goals"])
        assists += int(values["assists"])
    if player_id not in {int(pid) for pid in existing_by_player_id}:
        goals += int(update["goals"])
        assists += int(update["assists"])
    return {"goals":goals,"assists":assists}


def prepare_live_goal_change(*, home_score, away_score, home_team_id, away_team_id, team_id, delta=1):
    """Return the score transition for one atomic live-goal operation.

    Missing scores are treated as 0-0 only for live goal entry. The selected
    team must be one of the match participants and a correction may never
    produce a negative score.
    """
    home_team_id = int(home_team_id)
    away_team_id = int(away_team_id)
    team_id = int(team_id)
    delta = int(delta)
    if delta not in {-1, 1}:
        raise ValueError("delta must be -1 or 1")
    if team_id not in {home_team_id, away_team_id}:
        raise ValueError("team is not part of the match")
    old_home = int(home_score or 0)
    old_away = int(away_score or 0)
    new_home = old_home + (delta if team_id == home_team_id else 0)
    new_away = old_away + (delta if team_id == away_team_id else 0)
    if new_home < 0 or new_away < 0:
        raise ValueError("score cannot be negative")
    return {
        "old_home_score": old_home,
        "old_away_score": old_away,
        "home_score": new_home,
        "away_score": new_away,
    }


def validate_result_against_linked_goals(*, home_score, away_score, home_linked_goals, away_linked_goals):
    """Validate that a proposed result can still explain stored player goals.

    Player-linked goal counters may be lower than the team score (own goals or
    unknown scorer), but they may never exceed the corresponding team score.
    Clearing a result is also unsafe while linked player goals exist.
    """
    home_linked_goals = max(0, int(home_linked_goals or 0))
    away_linked_goals = max(0, int(away_linked_goals or 0))
    if home_score is None or away_score is None:
        if home_linked_goals or away_linked_goals:
            return {
                "ok": False,
                "message": "Ta bort registrerade målskyttar innan resultatet rensas.",
            }
        return {"ok": True, "message": ""}
    try:
        home_score = int(home_score)
        away_score = int(away_score)
    except (TypeError, ValueError):
        return {"ok": False, "message": "Resultatet måste bestå av hela, icke-negativa mål."}
    if home_score < 0 or away_score < 0:
        return {"ok": False, "message": "Resultatet kan inte innehålla negativa mål."}
    problems = []
    if home_linked_goals > home_score:
        problems.append(f"hemmalaget har {home_linked_goals} registrerade målskyttsmål men resultatet anger {home_score}")
    if away_linked_goals > away_score:
        problems.append(f"bortalaget har {away_linked_goals} registrerade målskyttsmål men resultatet anger {away_score}")
    if problems:
        return {
            "ok": False,
            "message": "Resultatet skulle inte stämma med matchhändelserna: " + "; ".join(problems) + ". Korrigera målskyttarna först.",
        }
    return {"ok": True, "message": ""}
