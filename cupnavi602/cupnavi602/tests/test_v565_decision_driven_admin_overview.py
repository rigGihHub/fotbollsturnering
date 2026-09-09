from cupnavi_core.admin_overview import build_admin_decision_summary


def _counts(**overrides):
    base = {
        "teams_n": 8,
        "groups_n": 2,
        "unassigned_n": 0,
        "pitches_n": 2,
        "matches_n": 12,
        "scheduled_n": 12,
        "played_n": 0,
    }
    base.update(overrides)
    return base


def test_v565_points_to_first_missing_setup_step():
    decision = build_admin_decision_summary(
        _counts(teams_n=3, groups_n=0, matches_n=0, scheduled_n=0),
        cupinfo_ready=True, expected_teams=8, rules_confirmed=False,
        schedule_dirty=False, published=False,
    )
    assert decision.title == "Nästa: Lag"
    assert decision.target == "Lag"
    assert decision.missing[0][0] == "Lag"
    assert [item[0] for item in decision.missing][:4] == ["Lag", "Regler", "Schema"] or [item[0] for item in decision.missing][:4] == ["Lag", "Regler", "Planer & tider", "Schema"]


def test_v565_unassigned_team_keeps_groups_incomplete():
    decision = build_admin_decision_summary(
        _counts(unassigned_n=1),
        cupinfo_ready=True, expected_teams=8, rules_confirmed=True,
        schedule_dirty=False, published=False,
    )
    assert decision.title == "Nästa: Grupper"
    assert "1 lag saknar grupp" in decision.text


def test_v565_requires_explicit_control_before_claiming_publish_ready():
    decision = build_admin_decision_summary(
        _counts(), cupinfo_ready=True, expected_teams=8, rules_confirmed=True,
        schedule_dirty=False, published=False, validation_ready=False,
    )
    assert decision.status == "control"
    assert decision.publish_ready is False
    assert decision.target == "Kontroller"


def test_v565_fresh_clean_validation_can_claim_publish_ready():
    decision = build_admin_decision_summary(
        _counts(), cupinfo_ready=True, expected_teams=8, rules_confirmed=True,
        schedule_dirty=False, published=False, validation_ready=True, validation_errors=(),
    )
    assert decision.status == "publish"
    assert decision.publish_ready is True
    assert decision.title == "Cupen är redo att publiceras"


def test_v565_validation_errors_keep_publication_blocked():
    decision = build_admin_decision_summary(
        _counts(), cupinfo_ready=True, expected_teams=8, rules_confirmed=True,
        schedule_dirty=False, published=False, validation_ready=True,
        validation_errors=("Krock", "Vila"),
    )
    assert decision.status == "blocked"
    assert decision.publish_ready is False
    assert "2 blockerande fel" in decision.text


def test_v565_dirty_schedule_is_actionable_and_never_publish_ready():
    decision = build_admin_decision_summary(
        _counts(), cupinfo_ready=True, expected_teams=8, rules_confirmed=True,
        schedule_dirty=True, published=False, validation_ready=True, validation_errors=(),
    )
    assert decision.title == "Nästa: Schema"
    assert decision.target == "Skapa och publicera schema"
    assert decision.publish_ready is False


def test_v565_first_run_markup_uses_current_nine_step_flow():
    source = open("app.py", encoding="utf-8").read()
    assert "9 · Publicera" in source
    assert "6 · Domare · valfritt" in source
    assert "Det här saknas före publicering" in source
    assert "build_admin_decision_summary" in source
