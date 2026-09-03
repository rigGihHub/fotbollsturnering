"""Pure HTML builders for the public match overview.

This module deliberately contains no Streamlit or database calls.  It is the
first small step in moving public rendering out of the monolithic app entrypoint
without changing behavior.
"""
from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, Sequence


def build_live_feed_html(
    items: Sequence[Mapping[str, Any]],
    *,
    is_live: bool,
    title: str,
    subtitle: str,
    status: str,
    row_value: Callable[[Mapping[str, Any], str, Any], Any],
    source_label: Callable[[Any], str],
    pitch_label: Callable[[Mapping[str, Any]], str],
) -> str:
    if not items:
        return ""
    cards: list[str] = []
    for match in items:
        try:
            dt = datetime.fromisoformat(str(row_value(match, "scheduled_start", "")))
            time_text = dt.strftime("%H:%M")
            date_text = (
                dt.strftime("%a %d %b")
                .replace("Mon", "Mån")
                .replace("Tue", "Tis")
                .replace("Wed", "Ons")
                .replace("Thu", "Tors")
                .replace("Fri", "Fre")
                .replace("Sat", "Lör")
                .replace("Sun", "Sön")
            )
        except (TypeError, ValueError):
            time_text, date_text = "–", ""
        home = html.escape(source_label(match["home_source"]))
        away = html.escape(source_label(match["away_source"]))
        pitch = html.escape(pitch_label(match))
        card_class = "cn-live-card is-live" if is_live else "cn-live-card"
        cards.append(
            f"<div class='{card_class}'>"
            f"<div class='cn-live-card-top'><div><div class='cn-live-time'>{html.escape(time_text)}</div>"
            f"<div class='cn-live-date'>{html.escape(date_text)}</div></div>"
            f"<div class='cn-live-pitch'>📍 {pitch}</div></div>"
            f"<div class='cn-live-teams'>{home}<span class='cn-live-vs'> – </span>{away}</div>"
            f"</div>"
        )
    return (
        "<section class='cn-live-strip'>"
        "<div class='cn-live-head'><div class='cn-live-head-left'><span class='cn-live-dot'></span>"
        f"<div><div class='cn-live-title'>{html.escape(title)}</div>"
        f"<div class='cn-live-subtitle'>{html.escape(subtitle)}</div></div></div>"
        f"<div class='cn-live-status'>{html.escape(status)}</div></div>"
        f"<div class='cn-live-grid'>{''.join(cards)}</div>"
        "</section>"
    )


def _team_names(names: Iterable[Any]) -> str:
    cleaned = [str(name) for name in names if str(name).strip()]
    if len(cleaned) <= 2:
        return " / ".join(cleaned)
    return f"{cleaned[0]} + {len(cleaned) - 1}"


def build_highlights_html(highlights: Mapping[str, Any], *, tr: Callable[[str], str]) -> str:
    cards: list[str] = []
    if "attack" in highlights:
        item = highlights["attack"]
        cards.append(
            f"<div class='cn-public-highlight'><div class='label'>⚽ {html.escape(tr('Flest gjorda mål'))}</div>"
            f"<div class='value'>{html.escape(_team_names(item['names']))}</div>"
            f"<div class='sub'>{int(item['value'])} {html.escape(tr('Mål').lower())}</div></div>"
        )
    if "defence" in highlights:
        item = highlights["defence"]
        cards.append(
            f"<div class='cn-public-highlight'><div class='label'>🛡️ {html.escape(tr('Minst insläppta'))}</div>"
            f"<div class='value'>{html.escape(_team_names(item['names']))}</div>"
            f"<div class='sub'>{int(item['value'])} {html.escape(tr('insläppta'))}</div></div>"
        )
    if "scorer" in highlights:
        item = highlights["scorer"]
        cards.append(
            f"<div class='cn-public-highlight'><div class='label'>🎯 {html.escape(tr('Skytteligaledare'))}</div>"
            f"<div class='value'>{html.escape(item['player'])}</div>"
            f"<div class='sub'>{html.escape(item['team'])} · {int(item['value'])} {html.escape(tr('Mål').lower())}</div></div>"
        )
    if "assist" in highlights:
        item = highlights["assist"]
        cards.append(
            f"<div class='cn-public-highlight'><div class='label'>✨ {html.escape(tr('Assistledare'))}</div>"
            f"<div class='value'>{html.escape(item['player'])}</div>"
            f"<div class='sub'>{html.escape(item['team'])} · {int(item['value'])} {html.escape(tr('Assist').lower())}</div></div>"
        )
    return f"<div class='cn-public-highlights'>{''.join(cards)}</div>" if cards else ""


def build_summary_html(
    *,
    team_count: int,
    played_count: int,
    total_matches: int,
    total_score: int,
    score_label: str,
    tr: Callable[[str], str],
    highlights_html: str = "",
) -> str:
    """Build the compact Matches summary with optional lightweight highlights.

    The core metrics still use already-loaded data. v391 allows a small highlight
    strip in the otherwise empty desktop space without restoring the full statistics
    dashboard to the Matches page.
    """
    return f"""<div class='cn-public-summary-row'>
      <div class='public-metric-grid'>
        <div class='public-metric'><div class='label'>{html.escape(tr('Lag'))}</div><div class='value'>{int(team_count)}</div></div>
        <div class='public-metric'><div class='label'>{html.escape(tr('Matcher spelade'))}</div><div class='value'>{int(played_count)} {html.escape(tr('av'))} {int(total_matches)}</div></div>
        <div class='public-metric'><div class='label'>{html.escape(str(score_label).capitalize())}</div><div class='value'>{int(total_score)}</div></div>
      </div>
      {highlights_html}
    </div>"""
