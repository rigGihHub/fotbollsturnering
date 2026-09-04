"""Fast, in-memory search helpers for CupNavi's public tournament view.

The public search intentionally works on snapshots that the workspace already
uses. It owns no database access and can therefore be tested without Streamlit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


@dataclass(frozen=True)
class PublicSearchResult:
    kind: str
    identity: int
    title: str
    subtitle: str = ""
    score: int = 0


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalize(value: Any) -> str:
    return " ".join(_text(value).casefold().split())


def _match_score(query: str, *values: Any) -> int:
    """Return a small deterministic relevance score, or zero when not matched."""
    q = _normalize(query)
    if not q:
        return 0
    best = 0
    for value in values:
        hay = _normalize(value)
        if not hay:
            continue
        if hay == q:
            best = max(best, 100)
        elif hay.startswith(q):
            best = max(best, 80)
        elif f" {q}" in hay:
            best = max(best, 65)
        elif q in hay:
            best = max(best, 50)
    return best


def build_public_search_results(
    query: str,
    *,
    teams: Sequence[Mapping[str, Any]],
    matches: Sequence[Mapping[str, Any]],
    pitches: Sequence[Mapping[str, Any]],
    team_names: Mapping[int, str],
    source_team_id: Callable[[Any], int | None],
    source_label: Callable[[Any], str],
    pitch_label: Callable[[Mapping[str, Any]], str],
    datetime_label: Callable[[Any], str],
    row_value: Callable[[Any, str, Any], Any],
    limit: int = 12,
) -> list[PublicSearchResult]:
    """Search teams, pitches and published matches without extra persistence work."""
    q = _normalize(query)
    if len(q) < 2:
        return []

    results: list[PublicSearchResult] = []

    for team in teams:
        team_id = int(row_value(team, "id", 0) or 0)
        name = _text(row_value(team, "name", ""))
        age_class = _text(row_value(team, "age_class", ""))
        score = _match_score(q, name, age_class, f"lag {name}")
        if score:
            results.append(PublicSearchResult("team", team_id, name or "Lag", age_class, score + 8))

    for pitch in pitches:
        pitch_no = int(row_value(pitch, "pitch_number", 0) or 0)
        name = _text(row_value(pitch, "name", "")) or f"Plan {pitch_no}"
        address = _text(row_value(pitch, "address", ""))
        score = _match_score(q, name, address, f"plan {pitch_no}", str(pitch_no))
        if score:
            subtitle = address or "Visa dagens matcher på planen"
            results.append(PublicSearchResult("pitch", pitch_no, name, subtitle, score + 6))

    for match in matches:
        match_id = int(row_value(match, "id", 0) or 0)
        home_source = row_value(match, "home_source", "")
        away_source = row_value(match, "away_source", "")
        home_id = source_team_id(home_source)
        away_id = source_team_id(away_source)
        home = team_names.get(home_id) if home_id is not None else None
        away = team_names.get(away_id) if away_id is not None else None
        # Do not resolve complex playoff sources here: the normal resolver may
        # read source matches/groups and would turn a public search into N+1 DB
        # work. Direct team sources cover the searchable team names; unresolved
        # bracket slots remain clear without sacrificing the search fast path.
        home = _text(home or "Ej klart")
        away = _text(away or "Ej klart")
        pitch = _text(pitch_label(match))
        stage = _text(row_value(match, "stage", ""))
        start = _text(datetime_label(row_value(match, "scheduled_start", "")))
        score = _match_score(
            q,
            home,
            away,
            f"{home} {away}",
            f"{home} - {away}",
            pitch,
            stage,
            f"match {match_id}",
            str(match_id),
        )
        if score:
            subtitle_parts = [part for part in (start, pitch, stage) if part]
            results.append(
                PublicSearchResult(
                    "match",
                    match_id,
                    f"{home} – {away}",
                    " · ".join(subtitle_parts),
                    score,
                )
            )

    kind_order = {"team": 0, "match": 1, "pitch": 2}
    results.sort(key=lambda item: (-item.score, kind_order.get(item.kind, 9), item.title.casefold(), item.identity))
    return results[: max(1, int(limit))]
