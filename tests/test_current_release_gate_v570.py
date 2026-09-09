from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
PREVIEW = (ROOT / "cupnavi_core" / "admin_publish_preview.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE_VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v570_version_is_synchronized():
    expected = "2026.09.09-570-CONTROL-PUBLIC-PREVIEW"
    assert VERSION == expected
    assert expected in APP
    assert expected in CORE_VERSION


def test_control_contains_real_visitor_facing_preview():
    assert "### 👀 Så kommer cupen att möta besökaren" in APP
    assert "Inget publiceras från den här förhandsgranskningen" in APP
    assert "show_heading=False" in APP
    assert APP.count("render_publish_preview(") >= 2


def test_preview_exposes_public_information_architecture():
    assert 'enabled_features = ["Cupinfo", "Matcher & schema", "Grupper & tabeller"]' in PREVIEW
    assert "enable_scorer_leaderboard" in PREVIEW
    assert "enable_assist_leaderboard" in PREVIEW
    assert "enable_card_statistics" in PREVIEW
    assert 'st.markdown("**Publikt innehåll**")' in PREVIEW


def test_preview_still_shows_core_content_before_publish():
    for text in ("Lag och grupper", "Schema", "Planer och platser", "Slutspel"):
        assert text in PREVIEW
    assert "Förhandsgranskningen ändrar ingenting" in PREVIEW


def test_control_still_keeps_publish_as_separate_deliberate_step():
    assert 'st.session_state[_control_focus_key] = "Publicera"' in APP
    assert "Fortsätt till Publicera →" in APP
    assert "render_admin_publication_controls(" in APP
