"""Sport-neutral CupNavi domain catalogue.

Canonical sport IDs are language independent. Localized display names are a UI concern.
Legacy Swedish sport names remain accepted for backward compatibility.
"""
from __future__ import annotations
from typing import Mapping

SPORTS = {
    "football": {"sv": "Fotboll", "en": "Football", "participant_type": "team", "period_label": {"sv": "halvlekar", "en": "halves"}, "score_label": {"sv": "mål", "en": "goals"}, "periods": 2, "minutes_per_period": 20, "break_minutes": 5, "minimum_rest_minutes": 45, "cards": True, "assists": True},
    "floorball": {"sv": "Innebandy", "en": "Floorball", "participant_type": "team", "period_label": {"sv": "perioder", "en": "periods"}, "score_label": {"sv": "mål", "en": "goals"}, "periods": 3, "minutes_per_period": 15, "break_minutes": 5, "minimum_rest_minutes": 45, "cards": False, "assists": True},
    "handball": {"sv": "Handboll", "en": "Handball", "participant_type": "team", "period_label": {"sv": "halvlekar", "en": "halves"}, "score_label": {"sv": "mål", "en": "goals"}, "periods": 2, "minutes_per_period": 20, "break_minutes": 5, "minimum_rest_minutes": 45, "cards": True, "assists": False},
    "ice_hockey": {"sv": "Ishockey", "en": "Ice hockey", "participant_type": "team", "period_label": {"sv": "perioder", "en": "periods"}, "score_label": {"sv": "mål", "en": "goals"}, "periods": 3, "minutes_per_period": 15, "break_minutes": 5, "minimum_rest_minutes": 60, "cards": False, "assists": True},
    "basketball": {"sv": "Basket", "en": "Basketball", "participant_type": "team", "period_label": {"sv": "perioder", "en": "periods"}, "score_label": {"sv": "poäng", "en": "points"}, "periods": 4, "minutes_per_period": 10, "break_minutes": 3, "minimum_rest_minutes": 45, "cards": False, "assists": False},
    "volleyball": {"sv": "Volleyboll", "en": "Volleyball", "participant_type": "team", "period_label": {"sv": "set", "en": "sets"}, "score_label": {"sv": "set", "en": "sets"}, "periods": 3, "minutes_per_period": 20, "break_minutes": 3, "minimum_rest_minutes": 45, "cards": False, "assists": False},
    "tennis": {"sv": "Tennis", "en": "Tennis", "participant_type": "individual_or_pair", "period_label": {"sv": "set", "en": "sets"}, "score_label": {"sv": "set", "en": "sets"}, "periods": 3, "minutes_per_period": 30, "break_minutes": 2, "minimum_rest_minutes": 60, "cards": False, "assists": False},
    "padel": {"sv": "Padel", "en": "Padel", "participant_type": "pair", "period_label": {"sv": "set", "en": "sets"}, "score_label": {"sv": "set", "en": "sets"}, "periods": 3, "minutes_per_period": 25, "break_minutes": 2, "minimum_rest_minutes": 45, "cards": False, "assists": False},
    "other": {"sv": "Annan", "en": "Other", "participant_type": "configurable", "period_label": {"sv": "perioder", "en": "periods"}, "score_label": {"sv": "poäng", "en": "points"}, "periods": 2, "minutes_per_period": 20, "break_minutes": 5, "minimum_rest_minutes": 45, "cards": False, "assists": False},
}

_ALIASES = {}
for _id, _sport in SPORTS.items():
    _ALIASES[_id.casefold()] = _id
    _ALIASES[_sport["sv"].casefold()] = _id
    _ALIASES[_sport["en"].casefold()] = _id


def sport_id(value: str | None) -> str:
    return _ALIASES.get(str(value or "football").strip().casefold(), "other")


def sport_definition(value: str | None) -> Mapping[str, object]:
    return SPORTS[sport_id(value)]


def sport_display_name(value: str | None, language: str = "sv") -> str:
    sport = sport_definition(value)
    lang = "en" if str(language).lower().startswith("en") else "sv"
    return str(sport[lang])


def legacy_profile(value: str | None, language: str = "sv") -> dict[str, object]:
    """Return the shape expected by the existing scheduling/UI code."""
    sport = sport_definition(value)
    lang = "en" if str(language).lower().startswith("en") else "sv"
    return {
        "sport_id": sport_id(value),
        "participant_type": sport["participant_type"],
        "period_label": sport["period_label"][lang],
        "score_label": sport["score_label"][lang],
        "halves": sport["periods"],
        "minutes_per_half": sport["minutes_per_period"],
        "halftime_minutes": sport["break_minutes"],
        "minimum_team_rest_minutes": sport["minimum_rest_minutes"],
        "cards": sport["cards"],
        "assists": sport["assists"],
    }
