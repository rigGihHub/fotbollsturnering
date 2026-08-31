from datetime import date
from pathlib import Path

from cupnavi_core.qol import TOURNAMENT_TEMPLATES, admin_mode, checklist_items, clone_tournament_payload


def test_templates_cover_multisport_onboarding():
    sports = {row["sport"] for row in TOURNAMENT_TEMPLATES.values()}
    assert {"Fotboll", "Innebandy", "Tennis", "Padel"}.issubset(sports)


def test_clone_resets_publication_and_preserves_foundation():
    source = {
        "location": "Örebro", "expected_team_count": 8,
        "points_win": 3, "points_draw": 1, "points_loss": 0,
        "playoff_format": "A-slutspel", "bronze_match": 1,
        "arena_address": "Arena 1", "kiosk_information": "Kiosk",
        "public_information": "Info", "organizer_phone": "123",
        "feedback_email": "a@example.com", "instagram_url": "",
        "table_tiebreak": "Målskillnad först", "playoff_tie_rule": "Straffar direkt",
        "extra_time_minutes": 0, "sport": "Fotboll", "locale": "sv-SE",
        "timezone_name": "Europe/Stockholm", "participant_type": "team", "country_code": "SE",
    }
    payload = clone_tournament_payload(source, name="Cup 2027", start_date="2027-06-01", end_date="2027-06-02")
    assert payload["name"] == "Cup 2027"
    assert payload["sport"] == "Fotboll"
    assert payload["is_published"] == 0
    assert payload["lifecycle_status"] == "draft"
    assert payload["schedule_dirty"] == 1


def test_admin_mode_detects_live_and_after():
    assert admin_mode("2026-08-24", "2026-08-25", "published", today=date(2026, 8, 24)) == "live"
    assert admin_mode("2026-08-24", "2026-08-25", "completed", today=date(2026, 8, 24)) == "after"
    assert admin_mode("2026-08-26", "2026-08-27", "draft", today=date(2026, 8, 24)) == "planning"


def test_checklist_has_action_targets():
    rows = checklist_items(teams=0, groups=0, matches=0, referees=0, published=False, public_contact=False)
    assert rows
    assert all(row["target"] for row in rows)
    assert not any(row["done"] for row in rows)


def test_app_contains_qol_entry_points():
    text = Path("app.py").read_text(encoding="utf-8")
    for needle in (
        "Startmall", "Duplicera tidigare cup", "Sök i cupen",
    ):
        assert needle in text
