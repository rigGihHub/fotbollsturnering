"""Pure public-view helpers, reusable by Streamlit and a future API/PWA."""
from __future__ import annotations

def match_summary(matches):
    played=[
        m for m in matches
        if m.get("home_score") is not None and m.get("away_score") is not None
    ]
    return {
        "total": len(matches),
        "played": len(played),
        "goals": sum(int(m.get("home_score") or 0)+int(m.get("away_score") or 0) for m in played),
    }

def filter_team_matches(matches, team_id, source_team_id):
    team_id=int(team_id)
    return [
        m for m in matches
        if team_id in (source_team_id(m.get("home_source")), source_team_id(m.get("away_source")))
    ]
