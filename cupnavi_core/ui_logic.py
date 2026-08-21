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
