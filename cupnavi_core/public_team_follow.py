"""Pure helpers for the public 'Mitt lag' experience.

The module deliberately has no Streamlit or database dependency.  It owns the
match selection/summary rules and the HTML for the team summary card, while the
Streamlit view keeps routing, persistence and interactive actions.
"""
from __future__ import annotations

from datetime import datetime
import html
from typing import Any, Callable, Iterable, Mapping


def match_datetime(match_row: Mapping[str, Any], row_value: Callable[[Any, str, Any], Any]) -> datetime | None:
    value = row_value(match_row, "scheduled_start", None)
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def build_favorite_team_snapshot(
    published_matches: Iterable[Mapping[str, Any]],
    team_id: int,
    *,
    now: datetime,
    source_team_id: Callable[[Any], int | None],
    row_value: Callable[[Any, str, Any], Any],
) -> dict[str, Any]:
    matches = [
        match for match in published_matches
        if team_id in (source_team_id(match["home_source"]), source_team_id(match["away_source"]))
    ]
    matches = sorted(
        matches,
        key=lambda match: (
            match_datetime(match, row_value) is None,
            match_datetime(match, row_value) or datetime.max,
        ),
    )
    next_match = next(
        (
            match for match in matches
            if row_value(match, "home_score", None) is None
            and row_value(match, "away_score", None) is None
            and match_datetime(match, row_value) is not None
            and match_datetime(match, row_value) >= now
        ),
        None,
    )
    latest_match = next(
        (
            match for match in reversed(matches)
            if row_value(match, "home_score", None) is not None
            and row_value(match, "away_score", None) is not None
        ),
        None,
    )
    played_count = 0
    wins = 0
    for match in matches:
        home_score = row_value(match, "home_score", None)
        away_score = row_value(match, "away_score", None)
        if home_score is None or away_score is None:
            continue
        played_count += 1
        home_id = source_team_id(match["home_source"])
        if (home_id == team_id and home_score > away_score) or (home_id != team_id and away_score > home_score):
            wins += 1
    return {
        "matches": matches,
        "next_match": next_match,
        "latest_match": latest_match,
        "played_count": played_count,
        "wins": wins,
    }


def build_favorite_team_hero_html(
    *,
    team_name: str,
    snapshot: Mapping[str, Any],
    now: datetime,
    table_position_text: str,
    possible_playoff: Mapping[str, Any] | None,
    row_value: Callable[[Any, str, Any], Any],
    source_label: Callable[[Any], str],
    pitch_label: Callable[[Any], str],
    swedish_datetime: Callable[[Any], str],
) -> str:
    next_match = snapshot.get("next_match")
    latest_match = snapshot.get("latest_match")
    matches = snapshot.get("matches") or []
    played_count = int(snapshot.get("played_count") or 0)

    content = (
        f"<div class='cn-follow-shell'><div class='cn-follow-kicker'>⭐ Mitt lag</div>"
        f"<div class='cn-follow-team'>{html.escape(team_name)}</div>"
    )
    if next_match:
        next_dt = match_datetime(next_match, row_value)
        minutes_until = max(0, int((next_dt - now).total_seconds() // 60)) if next_dt else None
        if minutes_until is None:
            relative_text = ""
        elif minutes_until < 60:
            relative_text = f" · om {minutes_until} min"
        elif minutes_until < 24 * 60:
            relative_text = f" · om {minutes_until // 60} h {minutes_until % 60:02d} min"
        else:
            relative_text = ""
        content += (
            f"<div class='cn-next-card'><div class='cn-next-meta'>Nästa match · "
            f"{html.escape(swedish_datetime(next_match['scheduled_start']))} · "
            f"{html.escape(pitch_label(next_match))}{html.escape(relative_text)}</div>"
            f"<div class='cn-next-teams'><div>{html.escape(source_label(next_match['home_source']))}</div>"
            f"<div class='cn-next-vs'>VS</div>"
            f"<div class='away'>{html.escape(source_label(next_match['away_source']))}</div></div></div>"
        )
    else:
        content += "<div class='cn-next-card'><div class='cn-next-meta'>Ingen kommande match är schemalagd just nu.</div></div>"

    latest_text = "–"
    if latest_match:
        latest_text = f"{latest_match['home_score']}–{latest_match['away_score']}"

    content += (
        "<div class='cn-follow-mini'>"
        f"<div><span>Matcher</span><strong>{len(matches)}</strong></div>"
        f"<div><span>Spelade</span><strong>{played_count}</strong></div>"
        f"<div><span>Senaste</span><strong>{html.escape(str(latest_text))}</strong></div>"
        "</div>"
        f"<div class='cn-my-status'><span class='cn-my-pill'>📊 Tabell: {html.escape(table_position_text)}</span>"
    )
    if possible_playoff and row_value(possible_playoff, "scheduled_start", None):
        content += (
            f"<span class='cn-my-pill'>🏆 {html.escape(str(row_value(possible_playoff, 'stage', 'Slutspel')))} · "
            f"{html.escape(swedish_datetime(possible_playoff['scheduled_start']))}</span>"
        )
    else:
        content += "<span class='cn-my-pill'>🏆 Slutspel: inväntar kvalificering</span>"
    return content + "</div></div>"


def favorite_team_group_id(
    public_teams: Iterable[Mapping[str, Any]],
    team_id: int,
    *,
    row_value: Callable[[Any, str, Any], Any],
) -> int | None:
    """Return the followed team's group id without depending on row type."""
    team_row = next(
        (row for row in public_teams if int(row["id"]) == int(team_id)),
        None,
    )
    value = row_value(team_row, "group_id", None) if team_row else None
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def favorite_table_position_label(table_rows: Iterable[Any], team_id: int) -> str:
    """Return Swedish ordinal label used by the public team card."""
    for index, row in enumerate(table_rows, 1):
        try:
            row_team_id = row[0]
            if int(row_team_id) == int(team_id):
                return f"{index}:a"
        except (TypeError, ValueError, IndexError, KeyError):
            continue
    return "–"


def find_possible_playoff(
    published_matches: Iterable[Mapping[str, Any]],
    team_id: int,
    *,
    source_team_id: Callable[[Any], int | None],
    row_value: Callable[[Any, str, Any], Any],
) -> Mapping[str, Any] | None:
    """Return the first unresolved non-group-stage match involving the team."""
    return next(
        (
            match for match in published_matches
            if row_value(match, "stage", "Gruppspel") != "Gruppspel"
            and team_id in (
                source_team_id(match["home_source"]),
                source_team_id(match["away_source"]),
            )
            and row_value(match, "home_score", None) is None
            and row_value(match, "away_score", None) is None
        ),
        None,
    )
