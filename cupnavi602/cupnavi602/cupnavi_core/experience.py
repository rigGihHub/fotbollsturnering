"""CupNavi experience helpers.

Pure helpers for multisport defaults, schedule impact analysis, quality scoring,
delay planning, playoff previews and tournament summaries. Kept independent of
Streamlit/database so the behavior is easy to regression test.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Iterable, Mapping, Sequence


from .sports import SPORTS, legacy_profile


# Backward-compatible display-keyed catalogue. New domain code should use
# cupnavi_core.sports and canonical language-independent sport IDs.
SPORT_PROFILES = {sport["sv"]: legacy_profile(sport_id) for sport_id, sport in SPORTS.items()}


def sport_profile(name: str | None) -> Mapping[str, object]:
    return legacy_profile(name)


def _rule_value(rules, key: str, default=None):
    """Read a rule from Mapping-like rows, including sqlite3.Row.

    sqlite3.Row supports ``row[key]`` but does not implement ``dict.get``.
    Keeping this adapter here prevents UI/database representation details from
    leaking into the duration calculation.
    """
    if rules is None:
        return default
    getter = getattr(rules, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            pass
    try:
        return rules[key]
    except (KeyError, IndexError, TypeError):
        return default


def match_duration_minutes(rules: Mapping[str, object] | None) -> int:
    periods = max(1, int(_rule_value(rules, "halves", 2) or 2))
    per_period = max(1, int(_rule_value(rules, "minutes_per_half", 20) or 20))
    break_minutes = max(0, int(_rule_value(rules, "halftime_minutes", 0) or 0))
    return periods * per_period + max(0, periods - 1) * break_minutes


def _dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def analyze_schedule_change(
    matches: Sequence[Mapping[str, object]],
    target_match_id: int,
    new_start,
    new_pitch: int | None,
    rules: Mapping[str, object] | None,
    resolve_team_id: Callable[[str], int | None],
) -> list[dict]:
    """Return structured conflicts/warnings for a proposed schedule move."""
    matches = [dict(m) for m in matches]
    target = next((m for m in matches if int(m.get("id") or 0) == int(target_match_id)), None)
    if not target:
        return [{"severity": "error", "code": "missing_match", "message": "Matchen finns inte."}]
    start = _dt(new_start)
    if start is None:
        return [{"severity": "error", "code": "invalid_start", "message": "Ogiltig starttid."}]

    rules = rules or {}
    duration = match_duration_minutes(rules)
    end = start + timedelta(minutes=duration)
    minimum_rest = max(0, int(rules.get("minimum_team_rest_minutes") or 0))
    pitch_break = max(0, int(rules.get("pitch_break_minutes") or 0))
    target_teams = {
        resolve_team_id(str(target.get("home_source") or "")),
        resolve_team_id(str(target.get("away_source") or "")),
    } - {None}
    target_ref = target.get("referee_id")
    issues: list[dict] = []

    for other in matches:
        if int(other.get("id") or 0) == int(target_match_id):
            continue
        other_start = _dt(other.get("scheduled_start"))
        if other_start is None:
            continue
        other_end = other_start + timedelta(minutes=duration)

        if new_pitch is not None and other.get("pitch_number") is not None and int(other.get("pitch_number")) == int(new_pitch):
            # include pitch turnover break
            if start < other_end + timedelta(minutes=pitch_break) and other_start < end + timedelta(minutes=pitch_break):
                issues.append({
                    "severity": "error",
                    "code": "pitch_overlap",
                    "other_match_id": int(other.get("id") or 0),
                    "message": f"Plan {new_pitch} krockar med match {other.get('match_no') or other.get('id')}.",
                })

        if target_ref and other.get("referee_id") and int(other.get("referee_id")) == int(target_ref):
            if start < other_end and other_start < end:
                issues.append({
                    "severity": "error",
                    "code": "referee_overlap",
                    "other_match_id": int(other.get("id") or 0),
                    "message": "Domaren är redan bokad i en annan match samtidigt.",
                })

        other_teams = {
            resolve_team_id(str(other.get("home_source") or "")),
            resolve_team_id(str(other.get("away_source") or "")),
        } - {None}
        common = target_teams & other_teams
        if not common:
            continue

        # Rest is measured end -> next start. Overlap becomes negative rest.
        if other_end <= start:
            rest = int((start - other_end).total_seconds() // 60)
        elif end <= other_start:
            rest = int((other_start - end).total_seconds() // 60)
        else:
            rest = -1
        if rest < minimum_rest:
            issues.append({
                "severity": "error" if rest < 0 else "warning",
                "code": "team_rest",
                "team_ids": sorted(common),
                "other_match_id": int(other.get("id") or 0),
                "rest_minutes": rest,
                "message": (
                    "Ett lag får en överlappande match."
                    if rest < 0
                    else f"Ett lag får bara {rest} minuters vila (minst {minimum_rest} krävs)."
                ),
            })

    return issues


def planned_delay_updates(
    matches: Sequence[Mapping[str, object]],
    pitch_number: int,
    delay_minutes: int,
    from_time=None,
) -> list[tuple[int, str]]:
    """Return match id + shifted ISO start for unplayed matches on a pitch."""
    matches = [dict(m) for m in matches]
    threshold = _dt(from_time) if from_time else None
    result = []
    for match in matches:
        if match.get("pitch_number") is None or int(match.get("pitch_number")) != int(pitch_number):
            continue
        if match.get("home_score") is not None and match.get("away_score") is not None:
            continue
        start = _dt(match.get("scheduled_start"))
        if start is None or (threshold and start < threshold):
            continue
        result.append((int(match.get("id") or 0), (start + timedelta(minutes=int(delay_minutes))).isoformat(timespec="minutes")))
    return result


def tournament_quality_score(
    tournament: Mapping[str, object],
    teams: Sequence[Mapping[str, object]],
    groups: Sequence[Mapping[str, object]],
    matches: Sequence[Mapping[str, object]],
    rules: Mapping[str, object] | None,
    schedule_issues: Sequence[Mapping[str, object]] | None = None,
) -> tuple[int, list[dict]]:
    """Conservative 0-100 readiness score with actionable deductions."""
    tournament = dict(tournament)
    teams = [dict(t) for t in teams]
    groups = [dict(g) for g in groups]
    matches = [dict(m) for m in matches]
    rules = dict(rules) if rules is not None else None
    score = 100
    findings: list[dict] = []

    def deduct(points, code, message, severity="warning"):
        nonlocal score
        score -= points
        findings.append({"code": code, "message": message, "severity": severity, "deduction": points})

    if not str(tournament.get("name") or "").strip():
        deduct(15, "name", "Turneringen saknar namn.", "error")
    if not str(tournament.get("start_date") or tournament.get("tournament_date") or "").strip():
        deduct(8, "date", "Cupdatum saknas.", "error")
    if not teams:
        deduct(25, "teams", "Inga lag/deltagare är registrerade.", "error")
    elif len(teams) < 4:
        deduct(5, "few_teams", "Få deltagare är registrerade; kontrollera att cupen är komplett.")
    ungrouped = [t for t in teams if t.get("group_id") is None]
    if groups and ungrouped:
        deduct(min(15, 2 * len(ungrouped)), "ungrouped", f"{len(ungrouped)} lag saknar grupp.", "error")
    if not matches:
        deduct(25, "matches", "Inga matcher är skapade.", "error")
    else:
        unscheduled = [m for m in matches if not m.get("scheduled_start")]
        if unscheduled:
            deduct(min(20, len(unscheduled)), "unscheduled", f"{len(unscheduled)} matcher saknar tid.", "error")
        no_pitch = [m for m in matches if m.get("scheduled_start") and m.get("pitch_number") is None]
        if no_pitch:
            deduct(min(12, len(no_pitch)), "pitch", f"{len(no_pitch)} schemalagda matcher saknar plan.", "error")
        no_ref = [m for m in matches if m.get("scheduled_start") and m.get("referee_id") is None]
        if rules and str(rules.get("referee_mode") or "") == "Automatisk" and no_ref:
            deduct(min(10, max(2, len(no_ref) // 2)), "referee", f"{len(no_ref)} matcher saknar domare.")
    if int(tournament.get("schedule_dirty") or 0):
        deduct(12, "dirty", "Schemat är markerat som inaktuellt.", "error")
    for issue in schedule_issues or []:
        severity = str(issue.get("severity") or "warning")
        deduct(5 if severity == "error" else 2, "schedule_issue", str(issue.get("message") or "Schemakonflikt."), severity)
    return max(0, min(100, score)), findings


def playoff_preview(group_tables: Mapping[str, Sequence[object]], playoff_format: str) -> list[str]:
    """Human-readable projection based on current standings, not a promise of final seeding.

    ``calculate_table`` in the Streamlit app returns ``(team_id, stats)`` tuples,
    while callers/tests may also provide plain mapping rows. Normalize both shapes
    here so the public playoff preview cannot crash merely because the table's
    internal representation changes.
    """
    normalized_tables: dict[str, list[dict]] = {}
    for name, rows in group_tables.items():
        normalized_rows: list[dict] = []
        for row in rows:
            if isinstance(row, Mapping):
                normalized_rows.append(dict(row))
                continue
            if (
                isinstance(row, (tuple, list))
                and len(row) >= 2
                and isinstance(row[1], Mapping)
            ):
                normalized_rows.append(dict(row[1]))
                continue
            # Unknown row shapes should not take down the whole public page.
            # They are ignored because a preview is informational only.
        normalized_tables[str(name)] = normalized_rows
    group_tables = normalized_tables
    fmt = str(playoff_format or "")
    if not group_tables or fmt == "Inget slutspel":
        return []
    lines: list[str] = []
    for group_name, rows in group_tables.items():
        if not rows:
            continue
        if "Placeringsslutspel" in fmt:
            for idx, row in enumerate(rows[:4], 1):
                lines.append(f"{idx}:a {group_name}: {row.get('Lag')}")
        else:
            for idx, row in enumerate(rows[:2], 1):
                lines.append(f"{idx}:a {group_name}: {row.get('Lag')}")
    return lines


def cup_summary(
    tournament: Mapping[str, object],
    teams: Sequence[Mapping[str, object]],
    matches: Sequence[Mapping[str, object]],
    top_scorer: Mapping[str, object] | None = None,
) -> dict:
    tournament = dict(tournament)
    teams = [dict(t) for t in teams]
    matches = [dict(m) for m in matches]
    top_scorer = dict(top_scorer) if top_scorer is not None else None
    played = [m for m in matches if m.get("home_score") is not None and m.get("away_score") is not None]
    total_score = sum(int(m.get("home_score") or 0) + int(m.get("away_score") or 0) for m in played)
    summary = {
        "name": str(tournament.get("name") or "CupNavi-turnering"),
        "sport": str(tournament.get("sport") or "Fotboll"),
        "teams": len(teams),
        "matches": len(matches),
        "played_matches": len(played),
        "total_score": total_score,
    }
    if top_scorer:
        summary["top_scorer"] = str(top_scorer.get("player_name") or "")
        summary["top_scorer_team"] = str(top_scorer.get("team_name") or "")
        summary["top_scorer_score"] = int(top_scorer.get("goals") or 0)
    return summary
