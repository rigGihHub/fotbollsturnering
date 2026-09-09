from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "2026.09.08-551-ALWAYS-VISIBLE-ADMIN-FLOW"


def test_current_release_version_is_synchronized():
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    core = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert version == EXPECTED
    assert f'APP_BUILD_VERSION = "{EXPECTED}"' in app
    assert f'APP_VERSION = "{EXPECTED}"' in core


def test_every_admin_page_gets_the_complete_seven_step_navigator():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Hela cupflödet" in app
    assert "Du är här: Steg {_step_no} av 7" in app
    assert "for _journey_row in (_BEGINNER_JOURNEY[:4], _BEGINNER_JOURNEY[4:]):" in app
    assert 'type="primary" if _active else "secondary"' in app
    assert "Alla steg är alltid åtkomliga." in app


def test_route_and_visible_step_are_always_synchronized():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.session_state[admin_flow_key] = _current_journey_step" in app
    assert "internal links must never leave the" in app
    assert "st.session_state[admin_page_key] = target" in app
    assert "st.session_state[admin_flow_key] = step_label" in app


def test_nested_admin_pages_explain_where_the_user_is():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"Domare": "Domare (valfritt)"' in app
    assert '_here_text += f" › {_subpage}"' in app
    assert '"Domare": "Planer & tider"' in app


def test_referee_flow_remains_optional_and_non_blocking():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    ux = (ROOT / "cupnavi_core" / "ux2.py").read_text(encoding="utf-8")
    assert 'Steg 4 · Planer & tider  /  Domare (valfritt)' in app
    assert 'Det stoppar inte publicering; domare kan tillsättas senare.' in app
    assert '"level": "info"' in ux
    assert '(missing_refs_n == 0, "Alla schemalagda matcher har domare")' not in app


def test_current_reporter_safety_contracts_remain_present():
    reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
    for token in ("Sparar", "Sparat", "Dåligt nät", "_setup_scorers", "_setup_assists", "_setup_cards"):
        assert token in reporter
