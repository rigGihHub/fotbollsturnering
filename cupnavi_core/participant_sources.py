"""Canonical participant-source contract used by CupNavi matches.

The persisted ``home_source``/``away_source`` fields already use these forms:
``team:<team_id>``, ``group:<group_id>:<placement>``, ``winner:<match_id>`` and
``loser:<match_id>``. This module centralizes parsing so newer code does not
reimplement or guess participant semantics from free text.
"""
from __future__ import annotations

from dataclasses import dataclass


_CANONICAL_KINDS = {"team", "group", "winner", "loser"}


@dataclass(frozen=True)
class ParticipantSource:
    kind: str
    raw: str
    source_id: int | None = None
    placement: int | None = None

    @property
    def canonical(self) -> bool:
        return self.kind in _CANONICAL_KINDS

    @property
    def is_dependency(self) -> bool:
        return self.kind in {"group", "winner", "loser"}


def _positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def parse_participant_source(value) -> ParticipantSource:
    """Parse one persisted participant source without interpreting legacy text.

    Recognized prefixes with malformed payloads return ``kind='invalid'`` so
    callers can distinguish corrupted canonical data from harmless legacy labels.
    Unknown text remains ``kind='legacy'`` and is never heuristically resolved.
    """
    raw = str(value or "").strip()
    if not raw:
        return ParticipantSource("empty", raw)

    parts = raw.split(":")
    prefix = parts[0].lower()
    if prefix not in _CANONICAL_KINDS:
        return ParticipantSource("legacy", raw)

    if prefix in {"team", "winner", "loser"}:
        if len(parts) != 2:
            return ParticipantSource("invalid", raw)
        source_id = _positive_int(parts[1])
        if source_id is None:
            return ParticipantSource("invalid", raw)
        return ParticipantSource(prefix, raw, source_id=source_id)

    if len(parts) != 3:
        return ParticipantSource("invalid", raw)
    group_id = _positive_int(parts[1])
    placement = _positive_int(parts[2])
    if group_id is None or placement is None:
        return ParticipantSource("invalid", raw)
    return ParticipantSource("group", raw, source_id=group_id, placement=placement)


def team_id_from_source(value) -> int | None:
    parsed = parse_participant_source(value)
    return parsed.source_id if parsed.kind == "team" else None
