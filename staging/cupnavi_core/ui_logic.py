"""Ren UI-logik som kan testas utan Streamlit."""

def match_belongs_to_team(home_team_id, away_team_id, selected_team_id):
    if selected_team_id is None:
        return True
    return selected_team_id in (home_team_id, away_team_id)

def schedule_issue_labels(referee_missing=False, color_conflict=False, home_unresolved=False, away_unresolved=False):
    issues = []
    if referee_missing:
        issues.append("Domare saknas")
    if color_conflict:
        issues.append("Färgkrock")
    if home_unresolved:
        issues.append("Hemmalag ej avgjort")
    if away_unresolved:
        issues.append("Bortalag ej avgjort")
    return issues


def sort_schedule_rows(rows):
    return sorted(
        rows,
        key=lambda row: (
            row.get("scheduled_start") or "",
            row.get("pitch_number") or 0,
            row.get("id") or 0,
        ),
    )

def filter_group_rows(rows, group_id):
    return [row for row in rows if row.get("group_id") == group_id]
