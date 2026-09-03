"""Preview-only recovery alternatives for a delayed pitch.

The engine compares conservative options and never writes tournament data.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Mapping, Sequence

from cupnavi_core.experience import analyze_schedule_change


def _value(row: Any, key: str, default=None):
    if row is None:
        return default
    if hasattr(row, "get"):
        return row.get(key, default)
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _dt(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value)) if value else None
    except (TypeError, ValueError):
        return None


def _team_ids(row, resolve_team_id: Callable[[str], int | None]) -> set[int]:
    return {
        team_id
        for team_id in (
            resolve_team_id(str(_value(row, "home_source", "") or "")),
            resolve_team_id(str(_value(row, "away_source", "") or "")),
        )
        if team_id is not None
    }


def _score_option(*, changed_matches: int, affected_teams: int, shifted_minutes: int, conflicts: int, unresolved_delay: int) -> int:
    return (
        int(conflicts) * 100_000
        + int(unresolved_delay) * 1_000
        + int(changed_matches) * 100
        + int(affected_teams) * 20
        + int(shifted_minutes)
    )


def _changed_summary(changes, by_id, resolve_team_id):
    team_ids: set[int] = set()
    shifted = 0
    for change in changes:
        row = by_id[int(change["match_id"])]
        team_ids |= _team_ids(row, resolve_team_id)
        old_start = _dt(row.get("scheduled_start"))
        new_start = _dt(change.get("scheduled_start"))
        if old_start and new_start:
            shifted += max(0, int((new_start - old_start).total_seconds() // 60))
    return len(changes), len(team_ids), shifted


def _validate_changes(matches, changes, rules, resolve_team_id):
    """Validate each move against the complete proposed final snapshot."""
    working = [dict(row) for row in matches]
    changes_by_id = {int(change["match_id"]): change for change in changes}
    for row in working:
        change = changes_by_id.get(int(row.get("id") or 0))
        if change:
            row["scheduled_start"] = change.get("scheduled_start")
            row["pitch_number"] = change.get("pitch_number")

    issues = []
    seen = set()
    for change in changes:
        target_id = int(change["match_id"])
        proposal_issues = analyze_schedule_change(
            working,
            target_id,
            change.get("scheduled_start"),
            int(change["pitch_number"]) if change.get("pitch_number") is not None else None,
            rules,
            resolve_team_id=resolve_team_id,
        )
        for issue in proposal_issues:
            # The same pair can be reported from both changed matches. Deduplicate
            # so the comparison score reflects distinct problems, not scan order.
            key = (
                issue.get("code"),
                min(target_id, int(issue.get("other_match_id") or target_id)),
                max(target_id, int(issue.get("other_match_id") or target_id)),
                tuple(issue.get("team_ids") or ()),
            )
            if key in seen:
                continue
            seen.add(key)
            issues.append(issue)
    conflicts = sum(1 for issue in issues if issue.get("severity") == "error")
    warnings = sum(1 for issue in issues if issue.get("severity") == "warning")
    return issues, conflicts, warnings


def compare_pitch_delay_recovery_options(
    matches: Sequence[Mapping[str, object]],
    *,
    pitch_number: int,
    delay_minutes: int,
    now: datetime,
    match_duration_minutes: int,
    pitch_break_minutes: int,
    rules: Mapping[str, object] | None,
    resolve_team_id: Callable[[str], int | None],
) -> list[dict]:
    """Compare recovery strategies for a delayed pitch.

    Options:
    - absorb gaps: delay only as long as needed and recover through scheduled gaps;
    - move next match: move just the first affected match to a free pitch when that
      creates enough space for the delayed pitch to recover;
    - shift all: conservative existing behavior;
    - do nothing: included as a baseline risk, never the preferred option while a
      known delay remains unresolved.
    """
    rows = [dict(row) for row in matches]
    by_id = {int(row.get("id") or 0): row for row in rows}
    pitch = int(pitch_number)
    delay = max(1, int(delay_minutes or 1))
    duration = timedelta(minutes=max(1, int(match_duration_minutes or 1)))
    turnover = timedelta(minutes=max(0, int(pitch_break_minutes or 0)))

    future = sorted(
        (
            row for row in rows
            if int(row.get("pitch_number") or 0) == pitch
            and _dt(row.get("scheduled_start")) is not None
            and _dt(row.get("scheduled_start")) > now
            and not (
                row.get("home_score") is not None
                and row.get("away_score") is not None
            )
        ),
        key=lambda row: (_dt(row.get("scheduled_start")), int(row.get("id") or 0)),
    )
    if not future:
        return []

    options = []

    # 1) Absorb the delay through existing schedule gaps.
    gap_changes = []
    carry = timedelta(minutes=delay)
    previous_end = None
    for index, row in enumerate(future):
        original = _dt(row["scheduled_start"])
        if index == 0:
            proposed = original + carry
        else:
            proposed = max(original, previous_end + turnover)
        if proposed > original:
            gap_changes.append({
                "match_id": int(row["id"]),
                "scheduled_start": proposed.isoformat(timespec="minutes"),
                "pitch_number": pitch,
            })
        previous_end = proposed + duration
    issues, conflicts, warnings = _validate_changes(rows, gap_changes, rules or {}, resolve_team_id)
    changed, teams, shifted = _changed_summary(gap_changes, by_id, resolve_team_id)
    options.append({
        "kind": "absorb_gaps",
        "title": "Låt luckorna äta upp förseningen",
        "detail": f"Flyttar {changed} match(er); schemat återgår automatiskt mot originaltider när luckorna räcker.",
        "changes": gap_changes,
        "changed_matches": changed,
        "affected_teams": teams,
        "shifted_minutes": shifted,
        "conflicts": conflicts,
        "warnings": warnings,
        "issues": issues,
        "unresolved_delay": 0,
    })

    # 2) Move only the next affected match to another free pitch if that frees
    # enough time for match number two to remain on its original time.
    first = future[0]
    first_start = _dt(first["scheduled_start"])
    all_pitches = sorted({
        int(row.get("pitch_number"))
        for row in rows
        if row.get("pitch_number") is not None
    })
    alternative_candidates = []
    if first_start is not None:
        second_start = _dt(future[1]["scheduled_start"]) if len(future) > 1 else None
        # After moving first away, the delayed pitch can recover if the next
        # remaining match starts after the expected delay window.
        recovery_deadline = first_start + timedelta(minutes=delay) + turnover
        can_recover_before_second = second_start is None or second_start >= recovery_deadline
        if can_recover_before_second:
            for alt_pitch in all_pitches:
                if alt_pitch == pitch:
                    continue
                changes = [{
                    "match_id": int(first["id"]),
                    "scheduled_start": first_start.isoformat(timespec="minutes"),
                    "pitch_number": alt_pitch,
                }]
                issues, conflicts, warnings = _validate_changes(rows, changes, rules or {}, resolve_team_id)
                if conflicts == 0:
                    changed, teams, shifted = _changed_summary(changes, by_id, resolve_team_id)
                    alternative_candidates.append({
                        "kind": "move_next",
                        "title": f"Flytta bara nästa match till Plan {alt_pitch}",
                        "detail": "Behåller matchtiden och frigör den försenade planen så att följande matcher kan ligga kvar.",
                        "changes": changes,
                        "changed_matches": changed,
                        "affected_teams": teams,
                        "shifted_minutes": shifted,
                        "conflicts": conflicts,
                        "warnings": warnings,
                        "issues": issues,
                        "unresolved_delay": 0,
                    })
    options.extend(alternative_candidates)

    # 3) Existing conservative full cascade.
    full_changes = []
    for row in future:
        start = _dt(row["scheduled_start"])
        full_changes.append({
            "match_id": int(row["id"]),
            "scheduled_start": (start + timedelta(minutes=delay)).isoformat(timespec="minutes"),
            "pitch_number": pitch,
        })
    issues, conflicts, warnings = _validate_changes(rows, full_changes, rules or {}, resolve_team_id)
    changed, teams, shifted = _changed_summary(full_changes, by_id, resolve_team_id)
    options.append({
        "kind": "shift_all",
        "title": f"Flytta alla senare matcher +{delay} min",
        "detail": f"Den säkra standardlösningen: {changed} match(er) förskjuts lika mycket.",
        "changes": full_changes,
        "changed_matches": changed,
        "affected_teams": teams,
        "shifted_minutes": shifted,
        "conflicts": conflicts,
        "warnings": warnings,
        "issues": issues,
        "unresolved_delay": 0,
    })

    # 4) Baseline: no schedule mutation, but known delay remains.
    affected_teams = set()
    for row in future:
        affected_teams |= _team_ids(row, resolve_team_id)
    options.append({
        "kind": "do_nothing",
        "title": "Gör ingenting ännu",
        "detail": f"Inga tider ändras, men cirka {delay} min känd försening lämnas olöst för {len(future)} kommande match(er).",
        "changes": [],
        "changed_matches": 0,
        "affected_teams": len(affected_teams),
        "shifted_minutes": 0,
        "conflicts": 0,
        "warnings": 0,
        "issues": [],
        "unresolved_delay": delay,
    })

    for option in options:
        option["score"] = _score_option(
            changed_matches=option["changed_matches"],
            affected_teams=option["affected_teams"],
            shifted_minutes=option["shifted_minutes"],
            conflicts=option["conflicts"],
            unresolved_delay=option["unresolved_delay"],
        )

    options.sort(key=lambda option: (
        option["score"],
        option["changed_matches"],
        option["affected_teams"],
        option["kind"],
    ))
    for index, option in enumerate(options):
        option["recommended"] = index == 0 and option["conflicts"] == 0 and option["unresolved_delay"] == 0
    return options


def compare_pitch_outage_recovery_options(
    matches: Sequence[Mapping[str, object]],
    *,
    pitch_number: int,
    now: datetime,
    rules: Mapping[str, object] | None,
    resolve_team_id: Callable[[str], int | None],
) -> list[dict]:
    """Preview conservative alternatives when one pitch becomes unavailable.

    The helper is read-only. It first tries to keep every remaining kickoff time
    unchanged and move affected matches to other pitches. If that cannot be done
    conflict-free, it also returns the best partial redistribution plus a baseline
    that leaves the schedule untouched for manual review.
    """
    rows = [dict(row) for row in matches]
    target_pitch = int(pitch_number)
    affected = sorted(
        (
            row for row in rows
            if int(row.get("pitch_number") or 0) == target_pitch
            and _dt(row.get("scheduled_start")) is not None
            and _dt(row.get("scheduled_start")) >= now
            and not (
                row.get("home_score") is not None
                and row.get("away_score") is not None
            )
        ),
        key=lambda row: (_dt(row.get("scheduled_start")), int(row.get("id") or 0)),
    )
    if not affected:
        return []

    all_pitches = sorted({
        int(row.get("pitch_number"))
        for row in rows
        if row.get("pitch_number") is not None and int(row.get("pitch_number") or 0) != target_pitch
    })
    by_id = {int(row.get("id") or 0): row for row in rows}

    placed = []
    unresolved = []
    working_changes = []
    for row in affected:
        found = None
        for alt_pitch in all_pitches:
            candidate = {
                "match_id": int(row["id"]),
                "scheduled_start": str(row.get("scheduled_start")),
                "pitch_number": int(alt_pitch),
            }
            trial_changes = working_changes + [candidate]
            _issues, conflicts, _warnings = _validate_changes(
                rows, trial_changes, rules or {}, resolve_team_id
            )
            if conflicts == 0:
                found = candidate
                working_changes = trial_changes
                placed.append(candidate)
                break
        if found is None:
            unresolved.append(int(row["id"]))

    options = []
    changed, teams, shifted = _changed_summary(placed, by_id, resolve_team_id) if placed else (0, 0, 0)
    issues, conflicts, warnings = _validate_changes(rows, placed, rules or {}, resolve_team_id) if placed else ([], 0, 0)
    if placed:
        complete = not unresolved
        options.append({
            "kind": "redistribute_same_times" if complete else "redistribute_partial",
            "title": (
                "Flytta matcherna till andra planer utan att ändra tider"
                if complete
                else "Flytta de matcher som får plats direkt"
            ),
            "detail": (
                f"Alla {len(affected)} berörda matcher kan behålla sina avsparkstider på andra planer."
                if complete
                else f"{len(placed)} av {len(affected)} matcher kan flyttas utan tidsändring; {len(unresolved)} kräver fortsatt planering."
            ),
            "changes": placed,
            "changed_matches": changed,
            "affected_teams": teams,
            "shifted_minutes": shifted,
            "conflicts": conflicts,
            "warnings": warnings,
            "issues": issues,
            "unresolved_matches": unresolved,
            "unresolved_count": len(unresolved),
        })

    affected_team_ids = set()
    for row in affected:
        affected_team_ids |= _team_ids(row, resolve_team_id)
    options.append({
        "kind": "manual_hold",
        "title": "Frys de berörda matcherna och planera om manuellt",
        "detail": (
            f"{len(affected)} återstående match(er) på Plan {target_pitch} berörs. "
            "Inga tider ändras förrän arrangören har valt lösning."
        ),
        "changes": [],
        "changed_matches": 0,
        "affected_teams": len(affected_team_ids),
        "shifted_minutes": 0,
        "conflicts": 0,
        "warnings": 0,
        "issues": [],
        "unresolved_matches": [int(row["id"]) for row in affected],
        "unresolved_count": len(affected),
    })

    def score(option):
        return (
            int(option.get("conflicts") or 0) * 100_000
            + int(option.get("unresolved_count") or 0) * 10_000
            + int(option.get("changed_matches") or 0) * 100
            + int(option.get("affected_teams") or 0) * 10
        )

    options.sort(key=lambda option: (score(option), option["kind"]))
    for idx, option in enumerate(options):
        option["recommended"] = idx == 0 and int(option.get("conflicts") or 0) == 0
    return options
