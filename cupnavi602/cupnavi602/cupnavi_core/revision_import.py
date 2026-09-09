"""Pure helpers for reviewing revised cup documents before anything is applied."""
from collections import defaultdict
from datetime import datetime, timedelta
import re

GROUP_RULE_FIELDS = (
    ("halves", "Halvlekar/perioder"),
    ("minutes_per_half", "Minuter per halvlek/period"),
    ("halftime_minutes", "Paus mellan halvlekar/perioder"),
    ("points_win", "Poäng för vinst"),
    ("points_draw", "Poäng för oavgjort"),
    ("points_loss", "Poäng för förlust"),
)

PLAYOFF_RULE_FIELDS = (
    ("halves", "Slutspel · halvlekar/perioder"),
    ("minutes_per_half", "Slutspel · minuter per halvlek/period"),
    ("halftime_minutes", "Slutspel · paus"),
    ("pitch_break_minutes", "Slutspel · planpaus"),
    ("tie_rule", "Slutspel · vid oavgjort"),
    ("extra_time_minutes", "Slutspel · förlängning"),
)


def explicit_values(payload, key):
    values = dict((payload or {}).get(key) or {})
    return {name: value for name, value in values.items() if value is not None and value != ""}


def normalize_tie_rule(value):
    text = " ".join(str(value or "").strip().casefold().split())
    if not text:
        return None
    if "förläng" in text and "straff" in text:
        return "Förlängning + straffar"
    if "straff" in text or "penalt" in text:
        return "Straffar direkt"
    if "lott" in text or "coin" in text:
        return "Lottning"
    return None


def revision_summary(payload):
    payload = payload or {}
    group = explicit_values(payload, "rule_values")
    playoff = explicit_values(payload, "playoff_rule_values")
    windows = [row for row in (payload.get("pitch_windows") or []) if isinstance(row, dict)]
    return {
        "group_rule_count": len(group),
        "playoff_rule_count": len(playoff),
        "pitch_window_count": len(windows),
        "match_count": len(payload.get("matches") or []),
        "playoff_match_count": len(payload.get("playoff_matches") or []),
        "warning_count": len(payload.get("warnings") or []),
    }


def _norm(value):
    """Conservative comparison normalizer; never strips squad/colour suffixes."""
    text = str(value or "").casefold().strip()
    text = re.sub(r"[^0-9a-zåäö]+", " ", text)
    return " ".join(text.split())


def _clock(value):
    text = str(value or "").strip()
    # scheduled_start may be ISO datetime while imported time is HH:MM.
    match = re.search(r"(?:T|\s)(\d{2}:\d{2})(?::\d{2})?$", text)
    if match:
        return match.group(1)
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"
    return text[:5] if len(text) >= 5 and ":" in text[:5] else text


def _team_rows(payload):
    out = []
    seen = set()
    for row in (payload or {}).get("teams") or []:
        name = " ".join(str((row or {}).get("name") or "").split())
        group = " ".join(str((row or {}).get("group_name") or "").split())
        key = _norm(name)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "group_name": group})
    return out


def _import_match_rows(payload):
    rows = []
    for row in (payload or {}).get("matches") or []:
        home = " ".join(str((row or {}).get("home_team") or "").split())
        away = " ".join(str((row or {}).get("away_team") or "").split())
        if not home or not away:
            continue
        rows.append({
            "phase": "group",
            "home": home,
            "away": away,
            "group": " ".join(str((row or {}).get("group_name") or "").split()),
            "time": _clock((row or {}).get("time")),
            "venue": " ".join(str((row or {}).get("venue") or "").split()),
        })
    for row in (payload or {}).get("playoff_matches") or []:
        home = " ".join(str((row or {}).get("home_source") or "").split())
        away = " ".join(str((row or {}).get("away_source") or "").split())
        if not home or not away:
            continue
        rows.append({
            "phase": "playoff",
            "home": home,
            "away": away,
            "group": "",
            "time": _clock((row or {}).get("time")),
            "venue": " ".join(str((row or {}).get("venue") or "").split()),
        })
    return rows


def _fixture_key(row):
    pair = sorted((_norm(row.get("home")), _norm(row.get("away"))))
    phase = str(row.get("phase") or "group")
    group = _norm(row.get("group")) if phase == "group" else ""
    return (phase, group, pair[0], pair[1])


def _display_fixture(row):
    prefix = f"{row.get('group')} · " if row.get("group") else ""
    return f"{prefix}{row.get('home')} – {row.get('away')}"



def build_match_revision_rows(current_matches, payload):
    """Return match-level revision rows for safe review/apply UI.

    Current rows may include database ids, scheduled date/time and played state.
    Imported rows are never applied here; this helper only classifies them.
    """
    current_rows = [dict(r) for r in (current_matches or []) if r.get("home") and r.get("away")]
    imported_rows = _import_match_rows(payload)
    cb, ib = defaultdict(list), defaultdict(list)
    for row in current_rows:
        row["time"] = _clock(row.get("time"))
        cb[_fixture_key(row)].append(row)
    for row in imported_rows:
        ib[_fixture_key(row)].append(row)
    for bucket in (cb, ib):
        for key in bucket:
            bucket[key].sort(key=lambda r: (_clock(r.get("time")), _norm(r.get("venue"))))

    out = []
    for key in sorted(set(cb) | set(ib)):
        old = cb.get(key, [])
        new = ib.get(key, [])
        paired = min(len(old), len(new))
        for idx in range(paired):
            before, after = old[idx], new[idx]
            changes = {}
            if after.get("time") and _clock(before.get("time")) != _clock(after.get("time")):
                changes["time"] = {"from": _clock(before.get("time")), "to": _clock(after.get("time"))}
            if after.get("venue") and _norm(before.get("venue")) != _norm(after.get("venue")):
                changes["venue"] = {"from": before.get("venue") or "", "to": after.get("venue") or ""}
            out.append({
                "status": "changed" if changes else "unchanged",
                "match": _display_fixture(after),
                "current": before,
                "proposed": after,
                "changes": changes,
                "safe_to_apply": bool(changes) and not bool(before.get("played")),
                "played": bool(before.get("played")),
            })
        for row in new[paired:]:
            out.append({"status": "new", "match": _display_fixture(row), "current": None, "proposed": row, "changes": {}, "safe_to_apply": False, "played": False})
        for row in old[paired:]:
            out.append({"status": "removed", "match": _display_fixture(row), "current": row, "proposed": None, "changes": {}, "safe_to_apply": False, "played": bool(row.get("played"))})
    return out


def merge_clock_into_scheduled_start(scheduled_start, new_clock):
    """Keep the existing match date and replace only HH:MM when possible."""
    old = str(scheduled_start or "").strip()
    clock = _clock(new_clock)
    if not re.fullmatch(r"[0-2]\d:[0-5]\d", clock or ""):
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})(?:T|\s)", old)
    if not m:
        return None
    return f"{m.group(1)}T{clock}:00"

def compare_revision_structure(current_teams, current_matches, payload):
    """Compare revised teams/groups/matches without mutating anything.

    current_teams: [{name, group_name}]
    current_matches: [{phase, home, away, group, time, venue}]
    payload: normalized AI document extraction.

    The function intentionally uses conservative exact normalized team identity.
    It reports differences only; it never decides how to apply them.
    """
    imported_teams = _team_rows(payload)
    current_by_name = {_norm(r.get("name")): r for r in (current_teams or []) if _norm(r.get("name"))}
    imported_by_name = {_norm(r.get("name")): r for r in imported_teams if _norm(r.get("name"))}

    added_teams = [imported_by_name[k]["name"] for k in sorted(imported_by_name.keys() - current_by_name.keys())]
    removed_teams = [current_by_name[k].get("name") for k in sorted(current_by_name.keys() - imported_by_name.keys())]
    group_moves = []
    for key in sorted(current_by_name.keys() & imported_by_name.keys()):
        before = " ".join(str(current_by_name[key].get("group_name") or "").split())
        after = " ".join(str(imported_by_name[key].get("group_name") or "").split())
        if after and _norm(before) != _norm(after):
            group_moves.append({"team": imported_by_name[key]["name"], "from": before or "Ingen grupp", "to": after})

    current_rows = [dict(r) for r in (current_matches or []) if r.get("home") and r.get("away")]
    imported_rows = _import_match_rows(payload)
    cb, ib = defaultdict(list), defaultdict(list)
    for row in current_rows:
        row["time"] = _clock(row.get("time"))
        cb[_fixture_key(row)].append(row)
    for row in imported_rows:
        ib[_fixture_key(row)].append(row)
    for bucket in (cb, ib):
        for key in bucket:
            bucket[key].sort(key=lambda r: (_clock(r.get("time")), _norm(r.get("venue"))))

    added_matches, removed_matches, changed_matches = [], [], []
    for key in sorted(set(cb) | set(ib)):
        old = cb.get(key, [])
        new = ib.get(key, [])
        paired = min(len(old), len(new))
        for idx in range(paired):
            before, after = old[idx], new[idx]
            changes = []
            if _clock(before.get("time")) != _clock(after.get("time")) and after.get("time"):
                changes.append(f"tid {_clock(before.get('time')) or '—'} → {_clock(after.get('time'))}")
            if _norm(before.get("venue")) != _norm(after.get("venue")) and after.get("venue"):
                changes.append(f"plan {before.get('venue') or '—'} → {after.get('venue')}")
            if changes:
                changed_matches.append({"match": _display_fixture(after), "changes": changes})
        added_matches.extend(_display_fixture(r) for r in new[paired:])
        removed_matches.extend(_display_fixture(r) for r in old[paired:])

    return {
        "added_teams": added_teams,
        "removed_teams": removed_teams,
        "group_moves": group_moves,
        "added_matches": added_matches,
        "removed_matches": removed_matches,
        "changed_matches": changed_matches,
        "counts": {
            "teams_added": len(added_teams),
            "teams_removed": len(removed_teams),
            "group_moves": len(group_moves),
            "matches_added": len(added_matches),
            "matches_removed": len(removed_matches),
            "matches_changed": len(changed_matches),
        },
    }



def _parse_dt(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def analyze_match_revision_impacts(
    selected_rows,
    all_matches,
    *,
    group_duration_minutes,
    playoff_duration_minutes,
    minimum_rest_minutes=0,
    pitch_windows=None,
):
    """Preview consequences of applying a set of match-level revision changes.

    This helper never mutates data. It builds one hypothetical schedule where all
    selected changes are applied together, then reports blockers/warnings for:
    pitch overlap, team overlap, referee overlap, confirmed pitch availability,
    and insufficient rest between a team's matches.
    """
    selected_by_id = {}
    for row in selected_rows or []:
        current = dict(row.get("current") or {})
        mid = int(current.get("id") or 0)
        if mid:
            selected_by_id[mid] = row

    hypothetical = []
    for raw in all_matches or []:
        match = dict(raw)
        mid = int(match.get("id") or 0)
        change = selected_by_id.get(mid)
        if change:
            if change.get("apply_start"):
                match["scheduled_start"] = change["apply_start"]
            if change.get("apply_pitch"):
                match["pitch_number"] = int(change["apply_pitch"])
        start = _parse_dt(match.get("scheduled_start"))
        if not start:
            continue
        phase = str(match.get("phase") or "group")
        duration = int(playoff_duration_minutes if phase == "playoff" else group_duration_minutes)
        duration = max(1, duration)
        match["_start"] = start
        match["_end"] = start + timedelta(minutes=duration)
        hypothetical.append(match)

    blockers, warnings = [], []
    seen = set()

    def add(target, code, text, match_ids):
        key = (code, tuple(sorted(int(x) for x in match_ids if x)))
        if key in seen:
            return
        seen.add(key)
        target.append({"code": code, "text": text, "match_ids": list(key[1])})

    # Hard overlaps: same pitch, team, or referee cannot be in two matches at once.
    for i, a in enumerate(hypothetical):
        for b in hypothetical[i + 1:]:
            if a["_start"] >= b["_end"] or b["_start"] >= a["_end"]:
                continue
            aids = [int(a.get("id") or 0), int(b.get("id") or 0)]
            if a.get("pitch_number") and a.get("pitch_number") == b.get("pitch_number"):
                add(blockers, "pitch_overlap", f"Plan {a.get('pitch_number')} får två matcher samtidigt: {a.get('home')} – {a.get('away')} och {b.get('home')} – {b.get('away')}.", aids)
            teams_a = {_norm(a.get("home")), _norm(a.get("away"))} - {""}
            teams_b = {_norm(b.get("home")), _norm(b.get("away"))} - {""}
            common = teams_a & teams_b
            if common:
                label = next((x for x in (a.get("home"), a.get("away")) if _norm(x) in common), "Ett lag")
                add(blockers, "team_overlap", f"{label} skulle spela två matcher samtidigt.", aids)
            if a.get("referee_id") and a.get("referee_id") == b.get("referee_id"):
                add(blockers, "referee_overlap", f"Samma domare skulle vara bokad på två matcher samtidigt.", aids)

    # Confirmed pitch windows are authoritative; unconfirmed windows are not blockers.
    window_map = {}
    for row in pitch_windows or []:
        if not bool(row.get("confirmed")):
            continue
        key = (int(row.get("pitch_number") or 0), str(row.get("play_date") or ""))
        window_map[key] = (str(row.get("start_time") or ""), str(row.get("end_time") or ""))
    for match in hypothetical:
        pitch = int(match.get("pitch_number") or 0)
        date = match["_start"].date().isoformat()
        window = window_map.get((pitch, date))
        if not window:
            continue
        start_clock = match["_start"].strftime("%H:%M")
        end_clock = match["_end"].strftime("%H:%M")
        if start_clock < window[0] or end_clock > window[1]:
            add(blockers, "pitch_window", f"{match.get('home')} – {match.get('away')} hamnar utanför Plan {pitch}s bekräftade tid {window[0]}–{window[1]}.", [match.get("id")])

    # Rest is a warning: organizer may deliberately approve a short turnaround.
    wanted_rest = max(0, int(minimum_rest_minutes or 0))
    if wanted_rest:
        by_team = defaultdict(list)
        for match in hypothetical:
            for team in (match.get("home"), match.get("away")):
                key = _norm(team)
                if key:
                    by_team[key].append((match["_start"], match["_end"], match, team))
        for rows in by_team.values():
            rows.sort(key=lambda x: x[0])
            for prev, nxt in zip(rows, rows[1:]):
                rest = int((nxt[0] - prev[1]).total_seconds() // 60)
                if 0 <= rest < wanted_rest:
                    add(warnings, "short_rest", f"{nxt[3]} får bara {rest} min vila mellan två matcher (målet är minst {wanted_rest} min).", [prev[2].get("id"), nxt[2].get("id")])

    selected_ids = set(selected_by_id)
    affected_blockers = [x for x in blockers if selected_ids & set(x.get("match_ids") or [])]
    affected_warnings = [x for x in warnings if selected_ids & set(x.get("match_ids") or [])]
    return {
        "blockers": affected_blockers,
        "warnings": affected_warnings,
        "can_apply": not bool(affected_blockers),
        "selected_count": len(selected_ids),
    }



def suggest_match_revision_resolutions(
    selected_rows,
    all_matches,
    *,
    group_duration_minutes,
    playoff_duration_minutes,
    minimum_rest_minutes=0,
    pitch_windows=None,
    max_shift_minutes=60,
    step_minutes=5,
):
    """Return ranked, preview-only fixes for blocking revision changes.

    The search is deliberately conservative: one selected match is adjusted at a
    time, first by trying another known pitch at the same kick-off, then by small
    time shifts on known pitches. A suggestion is returned only when the whole
    selected revision becomes blocker-free. Nothing is persisted here.
    """
    rows = [dict(r) for r in (selected_rows or [])]
    if not rows:
        return []

    base = analyze_match_revision_impacts(
        rows, all_matches,
        group_duration_minutes=group_duration_minutes,
        playoff_duration_minutes=playoff_duration_minutes,
        minimum_rest_minutes=minimum_rest_minutes,
        pitch_windows=pitch_windows,
    )
    if base.get("can_apply"):
        return []

    known_pitches = set()
    for match in all_matches or []:
        try:
            n = int(match.get("pitch_number") or 0)
        except Exception:
            n = 0
        if n:
            known_pitches.add(n)
    for win in pitch_windows or []:
        try:
            n = int(win.get("pitch_number") or 0)
        except Exception:
            n = 0
        if n:
            known_pitches.add(n)
    known_pitches = sorted(known_pitches)

    suggestions = []
    seen = set()
    for idx, row in enumerate(rows):
        current = dict(row.get("current") or {})
        mid = int(current.get("id") or 0)
        if not mid or row.get("played"):
            continue
        original_start = _parse_dt(row.get("apply_start") or current.get("scheduled_start"))
        original_pitch = int(row.get("apply_pitch") or current.get("pitch_number") or 0)
        if not original_start:
            continue

        candidates = []
        # Least invasive: same time, different existing pitch.
        for pitch in known_pitches:
            if pitch != original_pitch:
                candidates.append((original_start, pitch, 10 + abs(pitch-original_pitch)))
        # Then small shifts, preferring later over earlier at the same distance.
        for delta in range(step_minutes, max_shift_minutes + 1, step_minutes):
            for sign, sign_penalty in ((1, 0), (-1, 2)):
                start = original_start + timedelta(minutes=sign * delta)
                for pitch in ([original_pitch] if original_pitch else []) + [p for p in known_pitches if p != original_pitch]:
                    if not pitch:
                        continue
                    score = 20 + delta + (0 if pitch == original_pitch else 8) + sign_penalty
                    candidates.append((start, pitch, score))

        for start, pitch, score in candidates:
            variant = [dict(x) for x in rows]
            changed = dict(variant[idx])
            changed["apply_start"] = start.isoformat(timespec="minutes")
            changed["apply_pitch"] = int(pitch)
            variant[idx] = changed
            impact = analyze_match_revision_impacts(
                variant, all_matches,
                group_duration_minutes=group_duration_minutes,
                playoff_duration_minutes=playoff_duration_minutes,
                minimum_rest_minutes=minimum_rest_minutes,
                pitch_windows=pitch_windows,
            )
            if not impact.get("can_apply"):
                continue
            key = (mid, changed["apply_start"], changed["apply_pitch"])
            if key in seen:
                continue
            seen.add(key)
            time_changed = changed["apply_start"] != (row.get("apply_start") or current.get("scheduled_start"))
            pitch_changed = int(changed["apply_pitch"] or 0) != original_pitch
            parts = []
            if time_changed:
                parts.append(f"flytta till {start.strftime('%H:%M')}")
            if pitch_changed:
                parts.append(f"Plan {pitch}")
            suggestions.append({
                "match_id": mid,
                "match": row.get("match") or f"Match {mid}",
                "apply_start": changed["apply_start"],
                "apply_pitch": int(pitch),
                "title": " · ".join(parts) if parts else "Behåll matchen",
                "score": score,
                "warnings": impact.get("warnings") or [],
                "resolved_blockers": len(base.get("blockers") or []),
            })
            break

    suggestions.sort(key=lambda x: (x["score"], len(x.get("warnings") or []), x["match_id"]))
    return suggestions[:5]



def suggest_match_revision_resolution_plans(
    selected_rows,
    all_matches,
    *,
    group_duration_minutes,
    playoff_duration_minutes,
    minimum_rest_minutes=0,
    pitch_windows=None,
    max_shift_minutes=60,
    step_minutes=5,
    max_changed_matches=3,
    beam_width=24,
):
    """Return preview-only *multi-match* repair plans for a blocked revision.

    Unlike ``suggest_match_revision_resolutions`` this bounded beam search may
    adjust two or three selected, unplayed matches together. It remains
    deliberately conservative: only known pitches and small 5-minute time
    shifts are considered, and a plan is returned only when the complete
    selected revision is free from hard blockers under the normal consequence
    checker. Nothing is persisted here.
    """
    rows = [dict(r) for r in (selected_rows or [])]
    if not rows:
        return []
    base = analyze_match_revision_impacts(
        rows, all_matches,
        group_duration_minutes=group_duration_minutes,
        playoff_duration_minutes=playoff_duration_minutes,
        minimum_rest_minutes=minimum_rest_minutes,
        pitch_windows=pitch_windows,
    )
    if base.get("can_apply"):
        return []

    known_pitches = set()
    for match in all_matches or []:
        try:
            n = int(match.get("pitch_number") or 0)
        except Exception:
            n = 0
        if n:
            known_pitches.add(n)
    for win in pitch_windows or []:
        try:
            n = int(win.get("pitch_number") or 0)
        except Exception:
            n = 0
        if n:
            known_pitches.add(n)
    known_pitches = sorted(known_pitches)
    if not known_pitches:
        return []

    # Limit search to selected, unplayed matches that actually participate in a blocker.
    blocker_ids = {int(mid) for issue in (base.get("blockers") or []) for mid in (issue.get("match_ids") or []) if mid}
    editable = []
    for idx, row in enumerate(rows):
        cur = dict(row.get("current") or {})
        mid = int(cur.get("id") or 0)
        if not mid or row.get("played") or (blocker_ids and mid not in blocker_ids):
            continue
        start = _parse_dt(row.get("apply_start") or cur.get("scheduled_start"))
        pitch = int(row.get("apply_pitch") or cur.get("pitch_number") or 0)
        if start:
            editable.append((idx, mid, start, pitch, row.get("match") or f"Match {mid}"))
    if not editable:
        return []

    def candidates(start, pitch):
        out=[]
        # Same time, another pitch first.
        for p in known_pitches:
            if p != pitch:
                out.append((start, p, 10 + abs(p-pitch)))
        # Then small shifts. Prefer same pitch and later over earlier.
        for delta in range(step_minutes, max_shift_minutes + 1, step_minutes):
            for sign, sign_penalty in ((1, 0), (-1, 2)):
                st = start + timedelta(minutes=sign*delta)
                ordered = ([pitch] if pitch else []) + [p for p in known_pitches if p != pitch]
                for p in ordered:
                    if not p:
                        continue
                    score = 20 + delta + (0 if p == pitch else 8) + sign_penalty
                    out.append((st, p, score))
        # Keep the branch factor bounded and deterministic.
        seen=set(); compact=[]
        for st,p,score in sorted(out, key=lambda x:(x[2], x[0], x[1])):
            k=(st.isoformat(timespec='minutes'), int(p))
            if k in seen:
                continue
            seen.add(k); compact.append((st,p,score))
            if len(compact) >= 18:
                break
        return compact

    # State: (rows_variant, overrides, score, impact)
    states=[(rows, {}, 0, base)]
    solutions=[]
    visited=set()
    for depth in range(1, min(max_changed_matches, len(editable)) + 1):
        next_states=[]
        for variant, overrides, score0, impact0 in states:
            already=set(overrides)
            # Prefer editing matches that still participate in a blocker.
            active_ids={int(mid) for issue in (impact0.get('blockers') or []) for mid in (issue.get('match_ids') or []) if mid}
            choices=[e for e in editable if e[1] not in already and (not active_ids or e[1] in active_ids)]
            for idx, mid, original_start, original_pitch, label in choices:
                current_variant = variant[idx]
                base_start=_parse_dt(current_variant.get('apply_start') or (current_variant.get('current') or {}).get('scheduled_start')) or original_start
                base_pitch=int(current_variant.get('apply_pitch') or (current_variant.get('current') or {}).get('pitch_number') or original_pitch or 0)
                for start,pitch,cost in candidates(base_start, base_pitch):
                    new_variant=[dict(x) for x in variant]
                    changed=dict(new_variant[idx])
                    changed['apply_start']=start.isoformat(timespec='minutes')
                    changed['apply_pitch']=int(pitch)
                    new_variant[idx]=changed
                    new_overrides=dict(overrides)
                    new_overrides[mid]={'apply_start':changed['apply_start'], 'apply_pitch':int(pitch), 'match':label}
                    key=tuple(sorted((m,v['apply_start'],v['apply_pitch']) for m,v in new_overrides.items()))
                    if key in visited:
                        continue
                    visited.add(key)
                    imp=analyze_match_revision_impacts(
                        new_variant, all_matches,
                        group_duration_minutes=group_duration_minutes,
                        playoff_duration_minutes=playoff_duration_minutes,
                        minimum_rest_minutes=minimum_rest_minutes,
                        pitch_windows=pitch_windows,
                    )
                    total_score=score0+cost+25  # small penalty per extra changed match
                    if imp.get('can_apply'):
                        solutions.append((new_overrides,total_score,imp))
                    else:
                        # Beam heuristic: fewer blockers first, then lower movement cost.
                        next_states.append((new_variant,new_overrides,total_score,imp))
        if solutions:
            break
        next_states.sort(key=lambda s:(len(s[3].get('blockers') or []), s[2], len(s[3].get('warnings') or [])))
        states=next_states[:max(1,int(beam_width))]
        if not states:
            break

    plans=[]
    seen_plans=set()
    for overrides,score,impact in sorted(solutions, key=lambda x:(x[1], len(x[2].get('warnings') or []), len(x[0]))):
        key=tuple(sorted((m,v['apply_start'],v['apply_pitch']) for m,v in overrides.items()))
        if key in seen_plans:
            continue
        seen_plans.add(key)
        changes=[]
        for mid,ov in sorted(overrides.items()):
            start=_parse_dt(ov['apply_start'])
            changes.append({
                'match_id':int(mid),
                'match':ov.get('match') or f'Match {mid}',
                'apply_start':ov['apply_start'],
                'apply_pitch':int(ov['apply_pitch']),
                'title':f"{start.strftime('%H:%M') if start else ov['apply_start']} · Plan {int(ov['apply_pitch'])}",
            })
        plans.append({
            'changes':changes,
            'changed_match_count':len(changes),
            'score':score,
            'warnings':impact.get('warnings') or [],
            'resolved_blockers':len(base.get('blockers') or []),
        })
        if len(plans) >= 3:
            break
    return plans
