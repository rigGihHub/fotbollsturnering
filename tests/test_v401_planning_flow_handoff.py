from pathlib import Path

from cupnavi_core.admin_overview import build_readiness, recommend_next_step

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _counts(**overrides):
    base = {
        "teams_n": 8, "groups_n": 2, "unassigned_n": 0, "players_n": 0,
        "refs_n": 0, "matches_n": 12, "scheduled_n": 12, "played_n": 0,
        "missing_refs_n": 12, "unchecked_n": 8, "pitches_n": 2,
        "published_n": 0, "events_n": 0, "upcoming_n": 12,
        "missing_results_n": 12, "delayed_n": 0,
    }
    base.update(overrides)
    return base


def test_first_planning_handoff_goes_to_control_before_results():
    counts = _counts()
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=False)
    step = recommend_next_step(readiness, counts, schedule_dirty=False, published=False)
    assert step.target == "Kontroller"
    assert "publicera" in step.title.lower()


def test_optional_roster_and_referees_do_not_break_core_first_flow():
    counts = _counts(matches_n=0, scheduled_n=0, players_n=0, refs_n=0)
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=False)
    step = recommend_next_step(readiness, counts, schedule_dirty=False, published=False)
    assert step.target == "Skapa och publicera schema"


def test_published_cup_moves_into_result_work():
    counts = _counts()
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=False)
    step = recommend_next_step(readiness, counts, schedule_dirty=False, published=True)
    assert step.target == "Matcher och resultat"


def test_app_core_flow_no_longer_skips_control_for_unpublished_schedule():
    assert 'elif not bool(tournament["is_published"]):' in APP
    assert '_recommended_page, _recommended_label = "Kontroller", "Kontrollera och publicera"' in APP
    assert 'Steg 4 av 5 · Kontroll' in APP
