from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SCHEDULE=(ROOT/"cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_release_version():
    assert VERSION=="2026.09.07-520-UNIQUE-PUBLICATION-CHECKLIST-KEYS"

def test_workspace_headers_keep_step_context_without_duplicate_trail():
    assert 'render_clickable_planning_flow(st, tid=tid, current_step="Lag"' in APP
    assert 'render_clickable_planning_flow(st, tid=tid, current_step="Grupper"' in APP
    assert 'render_clickable_planning_flow(st, tid=tid, current_step="Kontroll"' in APP

def test_overview_uses_next_step_and_attention_without_duplicate_journey():
    assert "Rekommenderat nästa steg" in APP
    assert "Kräver din uppmärksamhet" in APP
    assert "cn-overview-journey" not in APP
    assert "flow_items = [" not in APP

def test_advanced_tools_are_quietly_named():
    assert '"Fler verktyg"' in APP
    assert '"Visa fler verktyg på översikten"' not in APP
    assert "Valfria schemaverktyg" in SCHEDULE

def test_public_primary_nav_has_no_forced_horizontal_scroll_on_mobile():
    assert "/* v385 — Logical flow + no-scroll public primary navigation */" in STYLE
    assert "overflow-x:visible!important" in STYLE
    assert "min-width:0!important" in STYLE
    assert "flex-wrap:wrap!important" in STYLE
    assert "flex:1 1 calc(33.333% - 4px)!important" in STYLE
