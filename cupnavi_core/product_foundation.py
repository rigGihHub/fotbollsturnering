"""Framework-independent product foundation for CupNavi v139.

Keeps product decisions out of Streamlit so a future API/PWA can reuse them.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

CORE_FEATURES = frozenset({
    "tournament", "competition_classes", "teams", "groups", "playing_areas",
    "rules", "schedule", "results", "standings", "playoffs", "publication",
})
OPTIONAL_FEATURES = frozenset({
    "checkin", "statistics", "messages", "functionaries", "sponsors",
    "offers", "fairness", "medical_info", "lost_found", "accessibility",
})
ADVANCED_FEATURES = frozenset({
    "travel_time", "advanced_schedule_rules", "api", "integrations",
})

@dataclass(frozen=True)
class WorkflowStep:
    key: str
    label: str
    target: str
    done: bool
    detail: str

def organizer_workflow(*, competition_classes: int, teams: int, expected_teams: int,
                       groups: int, pitches: int, rules_ready: bool, matches: int,
                       schedule_dirty: bool, published: bool) -> list[WorkflowStep]:
    """The organizer's task flow, independent of the current navigation layout."""
    team_done = teams > 0 and (expected_teams <= 0 or teams == expected_teams)
    return [
        WorkflowStep("basics", "Grunduppgifter", "Adminöversikt", True, "Turneringen är skapad"),
        WorkflowStep("classes", "Tävlingsklasser", "Adminöversikt", competition_classes > 0,
                     f"{competition_classes} klasser"),
        WorkflowStep("teams", "Lag", "Lag", team_done,
                     f"{teams} av {expected_teams}" if expected_teams else f"{teams} registrerade"),
        WorkflowStep("groups", "Grupper", "Grupper", groups > 0, f"{groups} grupper"),
        WorkflowStep("pitches", "Planer & tider", "Adminöversikt", pitches > 0, f"{pitches} spelytor"),
        WorkflowStep("rules", "Regler", "Adminöversikt", bool(rules_ready), "Tävlingsregler"),
        WorkflowStep("schedule", "Schema", "Skapa och publicera schema",
                     matches > 0 and not schedule_dirty,
                     "Aktuellt" if matches > 0 and not schedule_dirty else "Återstår"),
        WorkflowStep("publish", "Publicera", "Skapa och publicera schema", bool(published),
                     "Publicerad" if published else "Utkast"),
    ]

def workflow_summary(steps: Iterable[WorkflowStep]) -> dict:
    steps = list(steps)
    done = sum(1 for s in steps if s.done)
    total = len(steps)
    return {"done": done, "total": total, "percent": round(100 * done / total) if total else 0,
            "next": next((s for s in steps if not s.done), None)}

def enabled_feature_groups(settings: dict) -> dict[str, list[str]]:
    """Progressive disclosure: optional capabilities only surface when enabled."""
    optional = []
    mapping = {
        "enable_team_checkin": "checkin",
        "show_scorers": "statistics",
        "show_assists": "statistics",
        "show_cards": "statistics",
        "enable_fairness": "fairness",
        "consider_pitch_travel": "travel_time",
    }
    for setting, feature in mapping.items():
        if settings.get(setting) and feature not in optional:
            optional.append(feature)
    return {"core": sorted(CORE_FEATURES), "optional": sorted(optional)}
