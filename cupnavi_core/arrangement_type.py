"""Explicit CupNavi arrangement type helpers."""

ARRANGEMENT_TOURNAMENT = "tournament"
ARRANGEMENT_MATCHCAMP = "matchcamp"
VALID_ARRANGEMENT_TYPES = {ARRANGEMENT_TOURNAMENT, ARRANGEMENT_MATCHCAMP}


def normalize_arrangement_type(value):
    value = str(value or "").strip().lower()
    return value if value in VALID_ARRANGEMENT_TYPES else ARRANGEMENT_TOURNAMENT


def arrangement_label(value):
    return "Matchcamp" if normalize_arrangement_type(value) == ARRANGEMENT_MATCHCAMP else "Turnering"


def arrangement_setup_copy(value):
    if normalize_arrangement_type(value) == ARRANGEMENT_MATCHCAMP:
        return {
            "goal": "Fokus på bra matcher, jämn belastning och rimlig vila. Tabell och slutspel behövs normalt inte.",
            "results_recommended": False,
        }
    return {
        "goal": "Fokus på gruppspel, tabell och eventuellt slutspel med tydlig väg till placeringar.",
        "results_recommended": True,
    }
