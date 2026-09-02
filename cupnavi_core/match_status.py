"""Explicit match lifecycle shared by admin, reporter and public views."""
from __future__ import annotations

MATCH_NOT_STARTED = "not_started"
MATCH_LIVE = "live"
MATCH_HALFTIME = "halftime"
MATCH_FINISHED = "finished"

MATCH_STATUSES = (
    MATCH_NOT_STARTED,
    MATCH_LIVE,
    MATCH_HALFTIME,
    MATCH_FINISHED,
)

STATUS_LABELS = {
    MATCH_NOT_STARTED: "Ej startad",
    MATCH_LIVE: "Pågår",
    MATCH_HALFTIME: "Paus",
    MATCH_FINISHED: "Slut",
}


def normalize_match_status(value, *, has_result=False):
    text = str(value or "").strip().lower()
    aliases = {
        "not_started": MATCH_NOT_STARTED,
        "ej startad": MATCH_NOT_STARTED,
        "upcoming": MATCH_NOT_STARTED,
        "live": MATCH_LIVE,
        "pågår": MATCH_LIVE,
        "halftime": MATCH_HALFTIME,
        "paus": MATCH_HALFTIME,
        "finished": MATCH_FINISHED,
        "slut": MATCH_FINISHED,
        "spelad": MATCH_FINISHED,
    }
    if has_result:
        return MATCH_FINISHED
    return aliases.get(text, MATCH_NOT_STARTED)


def match_status_label(value, *, has_result=False):
    return STATUS_LABELS[normalize_match_status(value, has_result=has_result)]


def is_live_status(value):
    return normalize_match_status(value) in {MATCH_LIVE, MATCH_HALFTIME}
