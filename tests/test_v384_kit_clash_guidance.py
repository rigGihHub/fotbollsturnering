from pathlib import Path

from cupnavi_core.kit_clash_guidance import build_kit_guidance

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
STYLE = (ROOT / "cupnavi_core" / "style_system.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text().strip()


def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_clear_kits_need_no_action():
    result = build_kit_guidance(
        home_name="Lag A", away_name="Lag B",
        home_home_conflict=False, away_kit_used=False, unresolved_conflict=False,
    )
    assert result["state"] == "clear"
    assert result["needs_action"] is False
    assert result["away_kit"] == "home"


def test_home_home_conflict_is_resolved_by_away_kit():
    result = build_kit_guidance(
        home_name="Lag A", away_name="Lag B",
        home_home_conflict=True, away_kit_used=True, unresolved_conflict=False,
    )
    assert result["state"] == "resolved"
    assert result["needs_action"] is False
    assert result["away_kit"] == "away"
    assert "bortaställ" in result["short"]


def test_unresolved_conflict_requires_extra_kit():
    result = build_kit_guidance(
        home_name="Lag A", away_name="Lag B",
        home_home_conflict=True, away_kit_used=True, unresolved_conflict=True,
    )
    assert result["state"] == "conflict"
    assert result["needs_action"] is True
    assert result["away_kit"] == "extra"
    assert "extraställ" in result["short"]


def test_schedule_workspace_surfaces_only_real_remaining_conflicts():
    assert "unresolved_kit_conflict = bool(kit_color_conflict(home, away))" in WORKSPACE
    assert 'if row.get("Tröjstatus") == "conflict":' in WORKSPACE
    assert 'issues.append("Färgkrock")' in WORKSPACE
    assert 'startswith("⚠")' not in WORKSPACE


def test_schedule_workspace_summarizes_resolved_and_unresolved_kit_choices():
    assert "unresolved_kit_total" in WORKSPACE
    assert "switched_kit_total" in WORKSPACE
    assert "färgkrockar kräver åtgärd" in WORKSPACE
    assert "matcher lösta med bortaställ" in WORKSPACE
    assert "cn-kit-choice" in WORKSPACE


def test_visual_styles_exist_for_guidance_states():
    assert ".cn-kit-summary{" in STYLE
    assert ".cn-admin-match .cn-kit-choice{" in STYLE
    assert ".cn-admin-match .cn-kit-choice.resolved strong" in STYLE
    assert ".cn-admin-match .cn-kit-choice.conflict strong" in STYLE
