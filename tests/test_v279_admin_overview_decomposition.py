from pathlib import Path

from cupnavi_core.admin_overview import (
    build_control_status,
    build_organizer_overview,
    build_readiness,
    build_status_cards_html,
    build_workflow_html,
    class_progress_caption,
    recommend_next_step,
)
from cupnavi_core.admin_overview_repository import fetch_admin_workflow_counts

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
MODULE = (ROOT / "cupnavi_core" / "admin_overview.py").read_text(encoding="utf-8")
REPOSITORY = (ROOT / "cupnavi_core" / "admin_overview_repository.py").read_text(encoding="utf-8")
VERSION = "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"


def sample_counts(**overrides):
    counts = {
        "teams_n": 8,
        "groups_n": 2,
        "players_n": 80,
        "refs_n": 4,
        "matches_n": 12,
        "scheduled_n": 12,
        "played_n": 0,
        "missing_refs_n": 1,
        "unchecked_n": 2,
        "pitches_n": 2,
        "published_n": 0,
        "events_n": 0,
        "upcoming_n": 9,
        "missing_results_n": 3,
        "delayed_n": 1,
    }
    counts.update(overrides)
    return counts


def test_version_and_app_delegate_contract():
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()
    assert "fetch_admin_workflow_counts(one_row, int(tournament_id))" in APP
    assert "build_readiness(" in APP
    assert "recommend_next_step(" in APP
    overview = APP[APP.index('elif admin_page == "Adminöversikt":'):APP.index('if admin_page == "Cupinställningar":')]
    assert "build_organizer_overview(" not in overview
    assert "build_status_cards_html(" not in overview
    assert "build_workflow_html(" not in overview
    assert "organizer_workflow(" not in APP


def test_repository_preserves_single_query_snapshot_contract():
    captured = {}

    def query_one(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return {"teams_n": 8}

    result = fetch_admin_workflow_counts(query_one, 7)
    assert result == {"teams_n": 8}
    assert captured["sql"].count("SELECT COUNT(*)") >= 15
    assert "AS teams_n" in captured["sql"]
    assert "AS delayed_n" in captured["sql"]
    assert captured["params"][0] == 7
    assert len(captured["params"]) == 18


def test_readiness_and_next_step_follow_existing_priority():
    counts = sample_counts(teams_n=0, groups_n=0, players_n=0, refs_n=0, matches_n=0)
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=False)
    assert recommend_next_step(readiness, counts, schedule_dirty=False).target == "Lag"

    counts = sample_counts(groups_n=0, players_n=0, refs_n=0, matches_n=0)
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=False)
    assert recommend_next_step(readiness, counts, schedule_dirty=False).target == "Grupper"

    counts = sample_counts(matches_n=12, played_n=0)
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=True)
    assert recommend_next_step(readiness, counts, schedule_dirty=True).title == "Nästa steg: regenerera schema"

    counts = sample_counts(played_n=12)
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=False)
    assert readiness.results_ready is True
    assert recommend_next_step(readiness, counts, schedule_dirty=False, published=True).target == "Tabeller"


def test_control_status_and_organizer_model_are_pure():
    counts = sample_counts(delayed_n=2)
    cc = build_control_status(counts, schedule_dirty=True)
    assert cc == {
        "upcoming": 9,
        "missing_results": 3,
        "delayed": 2,
        "schedule_dirty": True,
        "problems": 3,
    }
    classes = [{"id": 1, "planned_team_count": 8}]
    rules = {"halves": 2, "minutes_per_half": 20, "pitch_count": 2, "minimum_team_rest_minutes": 15}
    model = build_organizer_overview(counts, class_rows=classes, sidebar_rules=rules, schedule_dirty=False, published=False)
    assert model["classes_n"] == 1
    assert model["expected_total"] == 8
    assert model["summary"]["total"] == len(model["steps"])


def test_html_and_class_caption_escape_dynamic_labels():
    counts = sample_counts()
    readiness = build_readiness(counts, expected_teams=8, schedule_dirty=False)
    status_html = build_status_cards_html(counts, expected_teams=8, published=False, schedule_dirty=False)
    workflow_html = build_workflow_html(counts, readiness)
    assert "Planerat: 8" in status_html
    assert "8 registrerade" in workflow_html
    caption = class_progress_caption(
        [{"id": 1, "planned_team_count": 8}],
        {1: 6},
        lambda row: "P14 <elit>",
    )
    # Caption is rendered by Streamlit as text, so it should preserve the display label.
    assert caption == "Lag per tävlingsklass · P14 <elit>: 6/8"


def test_admin_overview_modules_are_framework_agnostic():
    assert "import streamlit" not in MODULE
    assert "import streamlit" not in REPOSITORY
    assert "st." not in MODULE
    assert "st." not in REPOSITORY
