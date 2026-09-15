from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_bulk_search_reports_outcome_where_the_action_happens():
    ui=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text()
    assert "bulkKitResult" in ui
    assert "uppdaterade · ${uncertain} behöver förtydligas" in ui
    assert 'aria-live="polite"' in ui

def test_admin_uses_the_same_outlined_svg_shirt_as_public_view():
    ui=(ROOT/"frontend-next/src/components/admin-workspace.tsx").read_text()
    kit=(ROOT/"frontend-next/src/components/TeamKit.tsx").read_text()
    assert 'import { TeamKit }' in ui
    assert ui.count("<TeamKit primary={teamDraft.") == 2
    assert 'stroke="#101f2a"' in kit
