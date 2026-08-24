"""Quality-of-life helpers for CupNavi admin and onboarding.

This module stays UI-neutral so the same helpers can be reused by a future API/frontend.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


TOURNAMENT_TEMPLATES = {
    "custom": {
        "label_sv": "Egen konfiguration",
        "label_en": "Custom setup",
        "sport": "Fotboll",
        "expected_participants": 8,
        "description_sv": "Börja med neutrala standardvärden och anpassa själv.",
    },
    "youth_football": {
        "label_sv": "Ungdomsfotboll – grupp + slutspel",
        "label_en": "Youth football – groups + playoffs",
        "sport": "Fotboll",
        "expected_participants": 8,
        "description_sv": "Vanlig cupstart för ungdomsfotboll med gruppspel som grund.",
    },
    "floorball_cup": {
        "label_sv": "Innebandycup",
        "label_en": "Floorball cup",
        "sport": "Innebandy",
        "expected_participants": 8,
        "description_sv": "Sportprofil och standardvärden för innebandy.",
    },
    "tennis_knockout": {
        "label_sv": "Tennis – utslagsturnering",
        "label_en": "Tennis – knockout",
        "sport": "Tennis",
        "expected_participants": 16,
        "description_sv": "Individuella deltagare och setbaserad matchmodell.",
    },
    "padel_groups": {
        "label_sv": "Padel – grupp + slutspel",
        "label_en": "Padel – groups + playoffs",
        "sport": "Padel",
        "expected_participants": 16,
        "description_sv": "Par som deltagare och setbaserad matchmodell.",
    },
}


def template_definition(template_id: str) -> dict:
    return dict(TOURNAMENT_TEMPLATES.get(template_id) or TOURNAMENT_TEMPLATES["custom"])


def clone_tournament_payload(source: dict, *, name: str, start_date: str, end_date: str) -> dict:
    """Return safe tournament fields for a new edition.

    Publication/lifecycle state, slug and schedule dirtiness intentionally reset.
    """
    keys = (
        "location", "expected_team_count", "points_win", "points_draw", "points_loss",
        "playoff_format", "bronze_match", "arena_address", "kiosk_information",
        "public_information", "organizer_phone", "feedback_email", "instagram_url",
        "table_tiebreak", "playoff_tie_rule", "extra_time_minutes", "sport",
        "locale", "timezone_name", "participant_type", "country_code", "enable_team_checkin", "enable_final_ranking",
    )
    payload = {key: source.get(key) for key in keys}
    payload.update({
        "name": name.strip(),
        "tournament_date": start_date,
        "start_date": start_date,
        "end_date": end_date,
        "is_published": 0,
        "lifecycle_status": "draft",
        "schedule_dirty": 1,
    })
    return payload


def checklist_items(*, teams: int, groups: int, matches: int, referees: int, published: bool, public_contact: bool) -> list[dict]:
    return [
        {"label": "Deltagare registrerade", "done": teams > 0, "target": "Lag"},
        {"label": "Grupper/struktur skapad", "done": groups > 0, "target": "Grupper"},
        {"label": "Schema genererat", "done": matches > 0, "target": "Skapa och publicera schema"},
        {"label": "Domare/funktionärer förberedda", "done": referees > 0, "target": "Domare"},
        {"label": "Publik kontaktinformation klar", "done": public_contact, "target": "Adminöversikt"},
        {"label": "Cupen publicerad", "done": bool(published), "target": "Kontroller"},
    ]


def admin_mode(start_date: str | None, end_date: str | None, lifecycle_status: str, today: date | None = None) -> str:
    today = today or date.today()
    if lifecycle_status == "completed":
        return "after"
    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else start
    except ValueError:
        return "planning"
    if start and end and start <= today <= end:
        return "live"
    return "planning"
