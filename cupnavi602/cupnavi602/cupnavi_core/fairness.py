from collections import defaultdict
from datetime import datetime


def fairness_report(matches):
    """Return a transparent 0-100 schedule fairness score and findings.

    The function is sport-neutral: it only uses participant ids, scheduled time and pitch.
    """
    by_participant = defaultdict(list)
    for m in matches:
        start = m.get("scheduled_start") if isinstance(m, dict) else m["scheduled_start"]
        if not start:
            continue
        dt = datetime.fromisoformat(str(start))
        pitch = m.get("pitch_number") if isinstance(m, dict) else m["pitch_number"]
        for key in ("home_team_id", "away_team_id"):
            pid = m.get(key) if isinstance(m, dict) else m[key]
            if pid:
                by_participant[pid].append((dt, pitch))
    if not by_participant:
        return {"score": 100, "findings": ["Inte tillräckligt med schemalagda matcher för fairnessanalys."], "participants": 0}

    min_rests, early_counts, late_counts, pitch_changes = {}, {}, {}, {}
    for pid, items in by_participant.items():
        items.sort()
        rests = [int((b[0] - a[0]).total_seconds() // 60) for a, b in zip(items, items[1:])]
        min_rests[pid] = min(rests) if rests else None
        early_counts[pid] = sum(1 for dt, _ in items if dt.hour < 9)
        late_counts[pid] = sum(1 for dt, _ in items if dt.hour >= 18)
        pitch_changes[pid] = sum(1 for a, b in zip(items, items[1:]) if a[1] != b[1])

    penalty = 0
    findings = []
    rest_values = [v for v in min_rests.values() if v is not None]
    if rest_values:
        spread = max(rest_values) - min(rest_values)
        if spread > 90:
            penalty += 12; findings.append(f"Stor skillnad i kortaste vila mellan deltagare ({spread} min).")
        elif spread > 45:
            penalty += 6; findings.append(f"Viss skillnad i kortaste vila mellan deltagare ({spread} min).")
    early_spread = max(early_counts.values()) - min(early_counts.values())
    late_spread = max(late_counts.values()) - min(late_counts.values())
    if early_spread >= 2:
        penalty += 7; findings.append("Tidiga matcher är ojämnt fördelade.")
    if late_spread >= 2:
        penalty += 7; findings.append("Sena matcher är ojämnt fördelade.")
    change_spread = max(pitch_changes.values()) - min(pitch_changes.values())
    if change_spread >= 3:
        penalty += 6; findings.append("Plan-/spelplatsbyten är ojämnt fördelade.")
    if not findings:
        findings.append("Schemat har en jämn fördelning enligt analyserade fairnessmått.")
    return {"score": max(0, 100 - penalty), "findings": findings, "participants": len(by_participant)}
