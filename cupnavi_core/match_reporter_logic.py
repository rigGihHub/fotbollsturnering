"""Pure Match Reporter selection/projection logic.

No Streamlit/database imports. Persistence, optimistic locking and validation
remain in app.py.
"""


def select_playable_matches(matches, *, resolve_source):
    """Keep matches where both source expressions resolve to real teams."""
    return [
        row for row in matches
        if resolve_source(row["home_source"]) and resolve_source(row["away_source"])
    ]


def build_bulk_result_rows(
    matches,
    *,
    source_label,
    swedish_datetime,
    team_name_by_id,
):
    """Project match rows into the editable bulk-result table shape."""
    result=[]
    for match_row in matches:
        is_group = match_row["stage"] == "Gruppspel"
        result.append({
            "match_id": match_row["id"],
            "Match": swedish_datetime(match_row["scheduled_start"]),
            "Plan": match_row["pitch_number"],
            "Fas": match_row["stage"],
            "Hemmalag": source_label(match_row["home_source"]),
            "Hemmamål": match_row["home_score"],
            "Bortamål": match_row["away_score"],
            "Bortalag": source_label(match_row["away_source"]),
            "Hemmastraffar": match_row["home_penalties"] if not is_group else None,
            "Bortastraffar": match_row["away_penalties"] if not is_group else None,
            "Avgörande vinnare": (
                team_name_by_id.get(match_row["decided_winner_id"], "–")
                if not is_group else "–"
            ),
        })
    return result




RESULT_SNAPSHOT_FIELDS = (
    "home_score",
    "away_score",
    "home_penalties",
    "away_penalties",
    "decided_winner_id",
    "referee_id",
)


def result_snapshot(row):
    """Return the exact fields protected by optimistic locking.

    Supports dict-like objects and sqlite3.Row-style key access.
    """
    snapshot={}
    for key in RESULT_SNAPSHOT_FIELDS:
        getter=getattr(row, "get", None)
        if callable(getter):
            snapshot[key]=getter(key)
        else:
            snapshot[key]=row[key]
    return snapshot

def _optional_int(value, *, is_na):
    return None if is_na(value) else int(value)


def prepare_bulk_result_update(
    row,
    original,
    *,
    team_id_by_name,
    playoff_tie_rule,
    is_na,
):
    """Prepare one edited bulk-result row without performing persistence.

    Returns a dict with keys:
    - ``update``: optimistic-locking payload or None
    - ``info``: non-blocking guidance messages
    - ``errors``: blocking validation messages

    Persistence and conflict detection deliberately remain outside this helper.
    """
    match_id = int(row["match_id"])
    home_score = _optional_int(row["Hemmamål"], is_na=is_na)
    away_score = _optional_int(row["Bortamål"], is_na=is_na)
    home_penalties = _optional_int(row["Hemmastraffar"], is_na=is_na)
    away_penalties = _optional_int(row["Bortastraffar"], is_na=is_na)
    selected_decided = team_id_by_name.get(row["Avgörande vinnare"])

    changed = any([
        home_score != original["home_score"],
        away_score != original["away_score"],
        home_penalties != original["home_penalties"],
        away_penalties != original["away_penalties"],
        (
            row["Fas"] != "Gruppspel"
            and row["Avgörande vinnare"] != "–"
            and selected_decided != original["decided_winner_id"]
        ),
    ])
    if not changed:
        return {"update": None, "info": [], "errors": []}

    label = f"{row['Hemmalag']}–{row['Bortalag']}"
    if (home_score is None) != (away_score is None):
        return {
            "update": None,
            "info": [f"{label}: fyll i båda målresultaten."],
            "errors": [],
        }

    info = []
    errors = []
    decided_winner_id = None

    if row["Fas"] == "Gruppspel":
        home_penalties = None
        away_penalties = None
    elif home_score is not None and home_score == away_score:
        home_team_id = team_id_by_name.get(row["Hemmalag"])
        away_team_id = team_id_by_name.get(row["Bortalag"])

        if playoff_tie_rule == "Lottning":
            home_penalties = None
            away_penalties = None
            if selected_decided in (home_team_id, away_team_id):
                decided_winner_id = selected_decided
            else:
                info.append(f"{label}: välj vinnare av lottningen.")
        else:
            if home_penalties is not None or away_penalties is not None:
                if (
                    home_penalties is None
                    or away_penalties is None
                    or home_penalties == away_penalties
                ):
                    errors.append(f"{label}: ange ett komplett avgörande straffresultat.")
                    return {"update": None, "info": info, "errors": errors}
            else:
                info.append(f"{label}: ange straffresultat för att avgöra matchen.")
    else:
        home_penalties = None
        away_penalties = None

    update = {
        "match_id": match_id,
        "home_score": home_score,
        "away_score": away_score,
        "home_penalties": home_penalties,
        "away_penalties": away_penalties,
        "decided_winner_id": decided_winner_id,
        "referee_id": original["referee_id"],
        "expected": result_snapshot(original),
    }
    return {"update": update, "info": info, "errors": errors}
