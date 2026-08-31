from datetime import datetime
from pathlib import Path

from cupnavi_core.public_shell_view import _screen_matches_html, build_public_hero_html

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")


def test_release_version_v274():
    assert VERSION == "2026.08.31-353-GROUP-FLOW-PITCH-TIMING"


def test_public_hero_builder_preserves_status_and_escapes_content():
    tournament = {"name": "A < B", "location": "Örebro & Kumla", "sport": "Fotboll"}
    rendered = build_public_hero_html(
        tournament,
        lifecycle_status="live",
        cup_date_label=lambda _t: "28 aug",
        row_value=lambda row, key, default=None: row.get(key, default),
        translate=lambda text: text,
    )
    assert "cn-hero-status live" in rendered
    assert "● Pågår" in rendered
    assert "A &lt; B" in rendered
    assert "Örebro &amp; Kumla" in rendered
    assert "Turneringsöversikt" in rendered


def test_screen_match_builder_preserves_recent_score_and_pitch():
    start = datetime(2026, 8, 28, 18, 30)
    recent = [(start, {"home_score": 2, "away_score": 1}, "Lag <A> – Lag B")]
    upcoming = [(start, {"home_score": None, "away_score": None}, "Lag A – Lag B")]
    recent_html = _screen_matches_html(recent, "recent", pitch_label=lambda _m: "Plan 1")
    upcoming_html = _screen_matches_html(upcoming, "upcoming", pitch_label=lambda _m: "Plan <2>")
    assert "2–1" in recent_html
    assert "Lag &lt;A&gt; – Lag B" in recent_html
    assert "18:30" in upcoming_html
    assert "Plan &lt;2&gt;" in upcoming_html


def test_app_delegates_public_screen_and_hero_to_shell_module():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    module = (ROOT / "cupnavi_core" / "public_shell_view.py").read_text(encoding="utf-8")
    assert "from cupnavi_core.public_shell_view import build_public_hero_html, render_public_screen_mode" in app
    assert "render_public_screen_mode(" in WORKSPACE
    assert "build_public_hero_html(" in WORKSPACE
    assert "cn-screen-grid" not in WORKSPACE
    assert "SELECT * FROM sponsors WHERE tournament_id=? AND active=1" in module
