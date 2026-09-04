from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_mobile_playoff_links_exact_match_with_existing_direct_route():
    assert '"section": "matches"' in PRESENTATION
    assert '"match": str(match_row["id"])' in PRESENTATION
    assert 'href=\'{html.escape(match_href, quote=True)}\'' in PRESENTATION
    assert 'target=\'_self\'' in PRESENTATION


def test_mobile_playoff_live_action_is_explicit_and_preserves_team_context():
    assert 'action_label = "Följ matchen nu" if status_label in {"Pågår", "Paus"} else "Öppna match"' in PRESENTATION
    assert 'direct_params["team"] = requested_team' in PRESENTATION
    assert '.match-action.live-action' in PRESENTATION


def test_mobile_playoff_action_adds_no_database_query():
    start = PRESENTATION.index('path_hint = f"Vinnaren går vidare till')
    end = PRESENTATION.index('round_progress =', start)
    block = PRESENTATION[start:end]
    assert 'all_rows(' not in block
    assert 'one_row(' not in block
    assert 'st.rerun(' not in block


def test_v449_version_is_consistent():
    version = "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert f'APP_BUILD_VERSION = "{version}"' in APP
    assert version in (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == version
