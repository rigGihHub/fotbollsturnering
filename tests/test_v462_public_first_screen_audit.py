from pathlib import Path

VERSION = "2026.09.07-519-BEGINNER-E2E-REGRESSION"
APP = Path("app.py").read_text(encoding="utf-8")
FOLLOW = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def test_version_is_v462():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_latest_result_is_rendered_before_next_match_action():
    result_pos = FOLLOW.index("cn-follow-latest-result")
    action_pos = FOLLOW.index("_primary_match_action = favorite_team_primary_action_label")
    assert result_pos < action_pos


def test_latest_result_reuses_in_memory_snapshot():
    assert '_last = favorite_snapshot.get("latest_match")' in FOLLOW
    assert "_team_sections = favorite_team_match_sections(" in FOLLOW
    assert "_upcoming = _team_sections[\"upcoming\"]" in FOLLOW


def test_directions_remain_truly_lazy():
    assert 'f"📍 Hitta till {public_pitch_label(favorite_next)}"' in FOLLOW
    assert "show_directions = st.toggle" in FOLLOW
    assert "if show_directions:" in FOLLOW


def test_upcoming_matches_show_three_first():
    assert "_visible_upcoming = _upcoming[:3]" in FOLLOW
    assert 'st.markdown("**Kommande matcher**")' in FOLLOW


def test_latest_result_has_compact_mobile_style():
    assert ".cn-follow-latest-result{" in STYLE
    assert ".cn-follow-latest-result .teams" in STYLE
