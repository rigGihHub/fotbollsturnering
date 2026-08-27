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
