from cupnavi_core.revision_import import (
    analyze_match_revision_impacts,
    suggest_match_revision_resolution_plans,
)


def _m(mid, home, away, start, pitch):
    return {
        "id": mid,
        "phase": "group",
        "home": home,
        "away": away,
        "scheduled_start": start,
        "pitch_number": pitch,
        "played": False,
        "referee_id": None,
    }


def test_two_independent_blockers_can_be_repaired_as_one_plan():
    all_matches = [
        _m(1, "A", "B", "2026-09-20T10:00:00", 1),
        _m(2, "C", "D", "2026-09-20T10:00:00", 2),
        _m(3, "E", "F", "2026-09-20T11:00:00", 1),
        _m(4, "G", "H", "2026-09-20T11:00:00", 2),
    ]
    # Revised document moves match 1 onto match 2's pitch and match 3 onto match 4's pitch.
    selected = [
        {"match": "A – B", "current": all_matches[0], "apply_start": "2026-09-20T10:00:00", "apply_pitch": 2, "played": False},
        {"match": "E – F", "current": all_matches[2], "apply_start": "2026-09-20T11:00:00", "apply_pitch": 2, "played": False},
    ]
    before = analyze_match_revision_impacts(
        selected, all_matches,
        group_duration_minutes=20,
        playoff_duration_minutes=20,
    )
    assert not before["can_apply"]
    assert len(before["blockers"]) == 2

    plans = suggest_match_revision_resolution_plans(
        selected, all_matches,
        group_duration_minutes=20,
        playoff_duration_minutes=20,
        max_changed_matches=3,
    )
    assert plans
    assert plans[0]["changed_match_count"] == 2
    assert {c["match_id"] for c in plans[0]["changes"]} == {1, 3}


def test_plan_is_preview_only_and_each_candidate_is_collectively_safe():
    all_matches = [
        _m(1, "A", "B", "2026-09-20T10:00:00", 1),
        _m(2, "C", "D", "2026-09-20T10:00:00", 2),
        _m(3, "E", "F", "2026-09-20T11:00:00", 1),
        _m(4, "G", "H", "2026-09-20T11:00:00", 2),
    ]
    original = [dict(x) for x in all_matches]
    selected = [
        {"match": "A – B", "current": all_matches[0], "apply_start": "2026-09-20T10:00:00", "apply_pitch": 2, "played": False},
        {"match": "E – F", "current": all_matches[2], "apply_start": "2026-09-20T11:00:00", "apply_pitch": 2, "played": False},
    ]
    plans = suggest_match_revision_resolution_plans(
        selected, all_matches,
        group_duration_minutes=20,
        playoff_duration_minutes=20,
    )
    assert all_matches == original
    assert plans[0]["resolved_blockers"] == 2
    repaired = [dict(r) for r in selected]
    by_id = {c["match_id"]: c for c in plans[0]["changes"]}
    for row in repaired:
        mid = row["current"]["id"]
        if mid in by_id:
            row["apply_start"] = by_id[mid]["apply_start"]
            row["apply_pitch"] = by_id[mid]["apply_pitch"]
    after = analyze_match_revision_impacts(
        repaired, all_matches,
        group_duration_minutes=20,
        playoff_duration_minutes=20,
    )
    assert after["can_apply"]


def test_admin_ui_applies_whole_plan_only_to_review_overrides():
    app = open("app.py", encoding="utf-8").read()
    assert "CupNavi föreslår en gemensam lösning" in app
    assert "Använd hela lösningen i granskningen" in app
    assert "revision_resolution_overrides" in app
    assert "Ingenting sparas förrän du godkänner de valda matchändringarna" in app
