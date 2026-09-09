from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "2026.09.08-552-RULES-FIRST-ADMIN-FLOW"


def test_current_release_version_is_synchronized():
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    core = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert version == EXPECTED
    assert f'APP_BUILD_VERSION = "{EXPECTED}"' in app
    assert f'APP_VERSION = "{EXPECTED}"' in core


def test_rules_are_a_real_primary_step():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    nav = (ROOT / "cupnavi_core" / "planning_flow_nav.py").read_text(encoding="utf-8")
    assert '("Regler", "Regler")' in app
    assert '"Regler": "Regler"' in nav
    assert 'Steg 4 av 8' in app
    assert 'Cupens regler' in app
    assert 'Fortsätt till Planer & tider →' in app


def test_every_admin_page_gets_the_complete_eight_step_navigator():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Hela cupflödet" in app
    assert 'av {len(_BEGINNER_JOURNEY)}' in app
    assert "for _journey_row in (_BEGINNER_JOURNEY[:4], _BEGINNER_JOURNEY[4:8]):" in app
    assert 'type="primary" if _active else "secondary"' in app
    assert "Alla steg är alltid åtkomliga." in app


def test_secondary_pages_have_logical_step_ownership():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"Slutspel": "Regler"' in app
    assert '"Domare": "Planer & tider"' in app
    assert '"Funktionärer": "Planer & tider"' in app
    assert '"Åtkomst & koder": "Cupinfo"' in app


def test_rules_page_keeps_played_match_history_safe():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '_rules_locked = (not is_test_environment(tournament)) and _played_rules > 0' in app
    assert 'home_score IS NULL AND away_score IS NULL' in app
    assert 'schedule_dirty=1' in app


def test_referee_flow_remains_optional_and_non_blocking():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    ux = (ROOT / "cupnavi_core" / "ux2.py").read_text(encoding="utf-8")
    assert 'Steg 5 · Planer & tider  /  Domare (valfritt)' in app
    assert 'Det stoppar inte publicering; domare kan tillsättas senare.' in app
    assert '"level": "info"' in ux


def test_current_reporter_safety_contracts_remain_present():
    reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
    for token in ("Sparar", "Sparat", "Dåligt nät", "_setup_scorers", "_setup_assists", "_setup_cards"):
        assert token in reporter
