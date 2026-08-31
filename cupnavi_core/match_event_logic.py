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
