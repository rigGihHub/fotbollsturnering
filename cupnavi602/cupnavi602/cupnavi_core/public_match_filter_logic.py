"""Pure filtering helpers for the public match list."""

def filter_matches(
    matches,
    *,
    mode="all",
    selected=None,
    team_rows=None,
    source_team_id,
):
    """Filter public matches without Streamlit/session/database dependencies."""
    base=list(matches)
    mode=(mode or "all").lower()

    if mode == "age":
        allowed={
            int(team["id"]) for team in (team_rows or [])
            if str(team.get("age_class", "") or "").strip() == str(selected or "")
        }
        return [
            row for row in base
            if source_team_id(row["home_source"]) in allowed
            or source_team_id(row["away_source"]) in allowed
        ]

    if mode == "group":
        return [row for row in base if row["group_id"] == selected]

    if mode == "team":
        return [
            row for row in base
            if source_team_id(row["home_source"]) == selected
            or source_team_id(row["away_source"]) == selected
        ]

    if mode == "pitch":
        return [
            row for row in base
            if int(row["pitch_number"] or 0) == int(selected or 0)
        ]

    return base


def sort_public_matches(matches):
    return sorted(
        matches,
        key=lambda row: (
            row["scheduled_start"] or "",
            row["pitch_number"] or 0,
            row["id"],
        ),
    )
